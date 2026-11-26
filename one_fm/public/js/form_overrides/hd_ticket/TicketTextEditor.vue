<template>
  <HTextEditor
    v-if="expand"
    ref="e"
    :model-value="content"
    :placeholder="placeholder"
    :upload-function="uploadEditorImage"
    @update:model-value="$emit('update:content', $event)"
    @clear="() => $emit('update:attachments', [])"
  >
    <template #bottom-top>
      <div class="flex flex-wrap gap-2">
        <AttachmentItem
          v-for="a in attachments"
          :key="a.file_url"
          :label="a.file_name"
          :url="!['MOV', 'MP4'].includes(a.file_type) ? a.file_url : null"
        >
          <template #suffix>
            <LucideX
              class="size-4"
              @click.stop="
                () => {
                  $emit(
                    'update:attachments',
                    attachments.filter((b) => b.file_url !== a.file_url)
                  );
                  removeAttachmentFromServer(a.name);
                }
              "
            />
          </template>
        </AttachmentItem>
      </div>
    </template>
    <template #bottom-left>
      <span class="flex">
        <slot name="bottom-left" />
        <FileUploader
          :upload-args="{
            folder: 'Home/Helpdesk',
            private: true,
          }"
          @success="
            (f: File) => $emit('update:attachments', [...attachments, f])
          "
          @failure="() => toast.error('Error uploading file')"
        >
          <template #default="{ openFileSelector }">
            <Button theme="gray" variant="ghost" @click="openFileSelector()">
              <template #icon>
                <LucidePaperclip class="size-4" />
              </template>
            </Button>
          </template>
        </FileUploader>
      </span>
    </template>
    <template #top-right>
      <slot name="top-right" />
    </template>
    <template #top-bottom>
      <slot name="top-bottom" />
    </template>
    <template #bottom-right>
      <slot name="bottom-right" />
    </template>
  </HTextEditor>
  <div
    v-else
    class="flex w-full cursor-pointer items-center gap-2 rounded bg-gray-100 px-3.5 py-2 hover:bg-gray-200"
    @click="() => $emit('update:expand', !expand)"
  >
    <UserAvatar
      :name="authStore.userName"
      :image="authStore.userImage"
      size="sm"
    />
    <span class="text-base text-gray-700">
      {{ placeholder }}
    </span>
  </div>
</template>
<script setup lang="ts">
import {
  AttachmentItem,
  TextEditor as HTextEditor,
  UserAvatar,
} from "@/components";
import { useAuthStore } from "@/stores/auth";
import { File } from "@/types";
import { removeAttachmentFromServer } from "@/utils";
import { FileUploader, toast, useFileUpload } from "frappe-ui";
import { computed, onBeforeUnmount, ref, watch } from "vue";

interface P {
  content: string;
  placeholder: string;
  attachments: File[];
  expand?: boolean;
  uploadFunction?: Function;
}

interface E {
  (event: "update:content", content: string): void;
  (event: "update:attachments", attachments: File[]): void;
  (event: "update:expand", expand: boolean): void;
}

const props = withDefaults(defineProps<P>(), {
  expand: false,
});
defineEmits<E>();
const e = ref(null);
const editor = computed(() => e.value.editor);

/**
 * Upload for anything added from inside the editor. The caller's handler
 * wins; otherwise upload with the same arguments as the paperclip below, so
 * the file is private and in the helpdesk folder like every other ticket
 * attachment.
 */
function uploadEditorImage(file: any) {
  if (props.uploadFunction) {
    return props.uploadFunction(file);
  }
  return useFileUpload().upload(file, {
    folder: "Home/Helpdesk",
    private: true,
  });
}

/**
 * Take a dropped picture away from the editor's own drop handler. That
 * handler inserts a placeholder node, uploads, then swaps the placeholder
 * for the result, and the placeholder does not survive the content round
 * trip, so the picture is lost and the uploaded file is left orphaned on the
 * server. Upload first and insert the finished image, the way pasting
 * already behaves.
 */
async function handleImageDrop(event: DragEvent) {
  const images = Array.from(event.dataTransfer?.files || []).filter(
    (f: any) => f.type && f.type.startsWith("image/")
  );
  if (!images.length) return;

  const ed = e.value?.editor;
  if (!ed) return;

  event.preventDefault();
  event.stopPropagation();

  for (const image of images) {
    try {
      const uploaded: any = await uploadEditorImage(image);
      ed.chain().focus().setImage({ src: uploaded.file_url }).run();
    } catch (error) {
      toast.error(__("Error uploading file"));
    }
  }
}

/**
 * The listener goes on the parent, in the capture phase: on the ProseMirror
 * element itself it would run after ProseMirror's own, which is registered
 * first and wins at the target.
 */
let dropTarget: HTMLElement | null = null;

function detachDropHandler() {
  dropTarget?.removeEventListener("drop", handleImageDrop, true);
  dropTarget = null;
}

watch(
  () => e.value,
  (instance: any) => {
    detachDropHandler();
    const parent = instance?.editor?.view?.dom?.parentElement;
    if (!parent) return;
    parent.addEventListener("drop", handleImageDrop, true);
    dropTarget = parent;
  },
  { immediate: true, flush: "post" }
);

onBeforeUnmount(detachDropHandler);
const authStore = useAuthStore();
defineExpose({
  editor,
});
</script>
