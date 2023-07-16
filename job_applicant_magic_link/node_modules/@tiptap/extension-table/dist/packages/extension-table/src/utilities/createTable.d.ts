import { Fragment, Node as ProsemirrorNode, Schema } from '@tiptap/pm/model';
export declare function createTable(schema: Schema, rowsCount: number, colsCount: number, withHeaderRow: boolean, cellContent?: Fragment | ProsemirrorNode | Array<ProsemirrorNode>): ProsemirrorNode;
