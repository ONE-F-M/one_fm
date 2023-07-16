import { Fragment, Node as ProsemirrorNode, NodeType } from '@tiptap/pm/model';
export declare function createCell(cellType: NodeType, cellContent?: Fragment | ProsemirrorNode | Array<ProsemirrorNode>): ProsemirrorNode | null | undefined;
