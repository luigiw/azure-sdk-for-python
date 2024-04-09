import * as _ from "@ts-common/iterator"
import { MutableStringMap, StringMap } from "@ts-common/string-map"

export interface JsonObjectInterface extends StringMap<Json> {}

export type JsonObject = JsonObjectInterface & object

export interface JsonArrayInterface extends ReadonlyArray<Json> {}

export type JsonArray = JsonArrayInterface & object

export type JsonArrayOf<T extends Json> = readonly T[] & object

export type JsonPrimitive = null | boolean | string | number

export type JsonRef = JsonObject | JsonArray

export type Json = JsonPrimitive | JsonRef

export type MutableJsonObject = MutableStringMap<Json> & object

export type MutableJsonArray = Json[]

export type MutableJsonRef = MutableJsonObject | MutableJsonArray

export interface Visitor<T> {
    /**
     * null
     */
    readonly asNull: () => T
    /**
     * boolean
     */
    readonly asBoolean: (value: boolean) => T
    /**
     * string
     */
    readonly asString: (value: string) => T
    /**
     * number
     */
    readonly asNumber: (value: number) => T
    /**
     * Json[]
     */
    readonly asArray: (value: JsonArray) => T
    /**
     * JsonObject
     */
    readonly asObject: (value: JsonObject) => T
}

export const visit = <T>(value: Json, visitor: Visitor<T>) =>
    value === null ? visitor.asNull() :
    typeof value === "boolean" ? visitor.asBoolean(value) :
    typeof value === "string" ? visitor.asString(value) :
    typeof value === "number" ? visitor.asNumber(value) :
    _.isArray(value) ? visitor.asArray(value) :
    visitor.asObject(value)

// tslint:disable-next-line:no-unbound-method
export const parse: (str: string) => Json = JSON.parse

// tslint:disable-next-line:no-unbound-method
export const stringify: (json: Json) => string = JSON.stringify

export const isPrimitive = (value: Json): value is JsonPrimitive =>
    value === null || typeof value !== "object"

export const isObject = (value: Json): value is JsonObject =>
    value !== null && typeof value === "object" && !_.isArray(value)

export type JsonType = "null" | "boolean" | "string" | "number" | "object" | "array"

export const typeOf = (value: Json): JsonType =>
    visit<JsonType>(
        value,
        {
            asNull: () => "null",
            asBoolean: () => "boolean",
            asNumber: () => "number",
            asString: () => "string",
            asArray: () => "array",
            asObject: () => "object",
        }
    )

export type EmptyObject = { readonly [k in never]?: never }
