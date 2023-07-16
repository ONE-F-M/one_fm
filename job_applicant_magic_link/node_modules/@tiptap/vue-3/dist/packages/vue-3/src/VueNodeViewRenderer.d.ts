import { DecorationWithType, NodeViewRenderer, NodeViewRendererOptions } from '@tiptap/core';
import { Node as ProseMirrorNode } from '@tiptap/pm/model';
import { Decoration } from 'prosemirror-view';
import { Component, PropType } from 'vue';
export declare const nodeViewProps: {
    editor: {
        type: PropType<import("@tiptap/core").Editor>;
        required: true;
    };
    node: {
        type: PropType<ProseMirrorNode>;
        required: true;
    };
    decorations: {
        type: PropType<DecorationWithType[]>;
        required: true;
    };
    selected: {
        type: PropType<boolean>;
        required: true;
    };
    extension: {
        type: PropType<import("@tiptap/core").Node<any, any>>;
        required: true;
    };
    getPos: {
        type: PropType<() => number>;
        required: true;
    };
    updateAttributes: {
        type: PropType<(attributes: Record<string, any>) => void>;
        required: true;
    };
    deleteNode: {
        type: PropType<() => void>;
        required: true;
    };
};
export interface VueNodeViewRendererOptions extends NodeViewRendererOptions {
    update: ((props: {
        oldNode: ProseMirrorNode;
        oldDecorations: Decoration[];
        newNode: ProseMirrorNode;
        newDecorations: Decoration[];
        updateProps: () => void;
    }) => boolean) | null;
}
export declare function VueNodeViewRenderer(component: Component, options?: Partial<VueNodeViewRendererOptions>): NodeViewRenderer;
