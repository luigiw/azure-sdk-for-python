export type MapFunc<T, R> = <K extends keyof T>(v: T[K], k: K) => R

export const forEach = <T>(source: T, func: MapFunc<T, void>): void => {
    // tslint:disable-next-line:forin
    for (const key in source) {
        func(source[key], key)
    }
}

export type PropertyFactory<T, K extends keyof T> = (k: K) => T[K]

export type Factory<T> = {
    readonly [K in keyof T]-?: PropertyFactory<T, K>
}

export const copyProperty = <T>(value: T): (<K extends keyof T>(k: K) => T[K]) =>
    (k) => value[k]

export type Mutable<T> = {
    -readonly [K in keyof T]: T[K]
}

export type MutableOptional<T> = {
    [K in keyof T]?: T[K]
}

const fromMutableOptional = <T>(v: MutableOptional<T>): T => v as T

/**
 * Use this functions to assign optional properties.
 * The function will delete the property `k` if the given value is `undefined`.
 *
 * @param mutable an object
 * @param k a name of property
 * @param v a property value
 */
export const setMutableProperty = <T, K extends keyof T>(
    mutable: MutableOptional<T>,
    k: K,
    v: T[K] | undefined,
): void => {
    if (v !== undefined) {
        mutable[k] = v
    } else {
        // tslint:disable-next-line:no-dynamic-delete
        delete mutable[k]
    }
}

export const create = <T>(factory: Factory<T>): T => {
    const result: MutableOptional<T> = {}
    forEach(
        factory,
        (propertyFactory, k) => { setMutableProperty(result, k, propertyFactory(k)) },
    )
    return fromMutableOptional(result)
}

export type PartialFactory<T> = {
    readonly [K in keyof T]?: (v: T[K], k: K) => T[K]
}

export const copyCreate = <T>(source: T, factory: PartialFactory<T>): T => {
    const result: MutableOptional<T> = {}
    forEach(source, (v, k) => {
        setMutableProperty(result, k, v)
    })
    let changes = false
    forEach(factory, (propertyFactory, k) => {
        // tslint:disable-next-line:strict-type-predicates
        if (propertyFactory !== undefined) {
            const sourceValue = source[k]
            const newValue = propertyFactory(sourceValue, k)
            if (sourceValue !== newValue) {
                setMutableProperty(result, k, newValue)
                changes = true
            }
        }
    })
    return changes ? fromMutableOptional(result) : source
}

export const asMutable = <T>(source: T): Mutable<T> => source as Mutable<T>
