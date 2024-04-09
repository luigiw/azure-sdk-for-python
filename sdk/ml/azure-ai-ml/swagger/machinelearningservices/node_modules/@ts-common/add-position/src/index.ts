import * as iterator from "@ts-common/iterator"

export type Position = {
    /**
     * Line number. Starts with 1.
     */
    readonly line: number
    /**
     * Column number. Starts with 1.
     */
    readonly column: number
}

export type CharAndPosition = {
    /**
     * Character.
     */
    readonly c: string
    /**
     * Position.
     */
    readonly position: Position
}

export const addPosition = (i: iterator.Iterable<string>): iterator.IterableEx<CharAndPosition> =>
    iterator.flatScan(
        i,
        (position, c) => [
            c === "\n" ? { line: position.line + 1, column: 1 } : { line: position.line, column: position.column + 1 },
            [{ c, position }],
        ],
        { line: 1, column: 1}
    )
