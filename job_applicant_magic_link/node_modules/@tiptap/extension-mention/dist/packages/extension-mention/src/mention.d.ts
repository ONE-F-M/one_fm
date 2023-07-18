import { Node } from '@tiptap/core';
import { Node as ProseMirrorNode } from '@tiptap/pm/model';
import { PluginKey } from '@tiptap/pm/state';
import { SuggestionOptions } from '@tiptap/suggestion';
export declare type MentionOptions = {
    HTMLAttributes: Record<string, any>;
    renderLabel: (props: {
        options: MentionOptions;
        node: ProseMirrorNode;
    }) => string;
    suggestion: Omit<SuggestionOptions, 'editor'>;
};
export declare const MentionPluginKey: PluginKey<any>;
export declare const Mention: Node<MentionOptions, any>;
