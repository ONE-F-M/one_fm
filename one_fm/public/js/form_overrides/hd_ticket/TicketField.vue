<template>
  <div class="flex gap-2 pb-1 leading-5 items-center">
    <div class="w-[106px] shrink-0 truncate text-sm text-gray-600">
      <Tooltip :text="field.label">
        <span>{{ field.label }}</span>
      </Tooltip>
      <span v-if="field.required" class="text-red-500"> * </span>
    </div>
    <div
      class="-m-0.5 min-h-[28px] flex-1 items-center overflow-hidden p-0.5 text-base"
    >
      <!--
        Text Editor fields hold HTML. Rendering them through FormControl dumps
        the raw markup into a single-line <input> (and lets a stray keystroke
        write mangled HTML back to the DB on blur), so they get a rendered
        preview that opens a real editor instead.
      -->
      <template v-if="field.fieldtype === 'Text Editor'">
        <div
          class="min-h-[28px] rounded px-1.5 py-1 -mx-1.5"
          :class="
            isEditable
              ? 'cursor-pointer hover:bg-surface-gray-2'
              : 'cursor-default'
          "
          @click="openEditor"
        >
          <!-- eslint-disable-next-line vue/no-v-html -->
          <div
            v-if="hasContent"
            class="prose prose-sm max-w-none text-ink-gray-8 line-clamp-3 break-words"
            v-html="sanitizedValue"
          />
          <span v-else class="text-ink-gray-4">
            {{ field.placeholder || `Add ${field.label}` }}
          </span>
        </div>

        <Dialog
          v-model="showEditor"
          :options="{ size: '2xl' }"
        >
          <template #body-title>
            <h3 class="text-lg font-semibold text-ink-gray-9">
              {{ field.label }}
            </h3>
          </template>
          <template #body-content>
            <TextEditor
              :content="draft"
              :placeholder="field.placeholder || `Add ${field.label}`"
              :bubble-menu="true"
              :fixed-menu="true"
              editor-class="!prose-sm overflow-auto min-h-[180px] max-h-80 py-1.5 px-2 rounded-b border border-outline-gray-2 bg-surface-white"
              @change="(val) => (draft = val)"
            />
          </template>
          <template #actions>
            <div class="flex justify-end gap-2">
              <Button @click="showEditor = false">Cancel</Button>
              <Button variant="solid" @click="saveEditor">Save</Button>
            </div>
          </template>
        </Dialog>
      </template>

      <component
        v-else
        :is="component"
        :key="field.fieldname"
        :readonly="field.readonly"
        :disabled="field.disabled"
        class="form-control"
        :placeholder="field.placeholder || `Add ${field.label}`"
        :model-value="transValue"
        autocomplete="off"
        v-on="
          [...textFields, ...numberFields].includes(field.fieldtype)
            ? {
                blur: (event) => {
                  emitUpdate(field.fieldname, event.target.value);
                },
              }
            : {
                'update:model-value': (event) => {
                  emitUpdate(
                    field.fieldname,
                    event?.value || event?.target?.value || event
                  );
                },
              }
        "
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { Autocomplete, Link } from "@/components";
import { APIOptions, Field, FieldValue } from "@/types";
import { parseApiOptions } from "@/utils";
import {
  Button,
  createResource,
  DatePicker,
  DateTimePicker,
  dayjs,
  Dialog,
  FormControl,
  TextEditor,
  Tooltip,
} from "frappe-ui";
import sanitizeHtml from "sanitize-html";
import { computed, h, ref } from "vue";

interface P {
  field: Field;
  value: FieldValue;
}

interface R {
  fieldname: Field["fieldname"];
  value: FieldValue;
}

interface E {
  (event: "change", value: R);
}

const props = defineProps<P>();
const emit = defineEmits<E>();

const apiOptions = createResource({
  url: props.field.url_method,
  auto: !!props.field.url_method,
  transform: (data: APIOptions) => {
    return parseApiOptions(data);
  },
});

// "Text Editor" is deliberately absent: it holds HTML and is handled above.
const textFields = ["Long Text", "Small Text", "Text", "Data"];
const numberFields = ["Int", "Float", "Currency", "Percent"];

const showEditor = ref(false);
const draft = ref("");

const isEditable = computed(
  () => !props.field.readonly && !props.field.disabled
);

const sanitizedValue = computed(() =>
  sanitizeHtml(String(props.value ?? ""), {
    allowedTags: sanitizeHtml.defaults.allowedTags.concat(["img"]),
  })
);

// Strip tags to decide whether there is anything to show — an "empty" Text
// Editor value is still a wrapper div (e.g. <div class="ql-editor read-mode">).
const hasContent = computed(
  () => sanitizeHtml(sanitizedValue.value, { allowedTags: [] }).trim().length > 0
);

function openEditor() {
  if (!isEditable.value) return;
  draft.value = String(props.value ?? "");
  showEditor.value = true;
}

function saveEditor() {
  emitUpdate(props.field.fieldname, draft.value);
  showEditor.value = false;
}

const component = computed(() => {
  if (props.field.url_method) {
    return h(Autocomplete, {
      options: apiOptions.data,
    });
  } else if (props.field.fieldtype === "Link" && props.field.options) {
    return h(Link, {
      doctype: props.field.options,
      hideMe: true,
    });
  } else if (props.field.fieldtype === "Select") {
    return h(Autocomplete, {
      options: props.field.options
        .split("\n")
        .map((o) => ({ label: o, value: o })),
    });
  } else if (props.field.fieldtype === "Check") {
    return h(Autocomplete, {
      options: [
        {
          label: "Yes",
          value: 1,
        },
        {
          label: "No",
          value: 0,
        },
      ],
    });
  } else if (textFields.includes(props.field.fieldtype)) {
    return h(FormControl, {
      type: "text",
    });
  } else if (props.field.fieldtype === "Datetime") {
    return h(DateTimePicker, {
      format: `${window.date_format.toUpperCase()} ${window.time_format}`,
    });
  } else if (props.field.fieldtype === "Date") {
    return h(DatePicker, {
      id: props.field.fieldname,
      format: window.date_format.toUpperCase(),
    });
  } else {
    return h(FormControl);
  }
});

const transValue = computed(() => {
  const fieldtype = props.field.fieldtype;
  if (fieldtype === "Check") {
    return props.value ? "Yes" : "No";
  } else if (fieldtype === "Date") {
    if (!props.value) return props.value;
    return dayjs(props.value).format(window.date_format.toUpperCase());
  }
  return props.value;
});

function emitUpdate(fieldname: Field["fieldname"], value: FieldValue) {
  emit("change", { fieldname, value });
}
</script>
<style scoped>
:deep(.form-control input:not([type="checkbox"])),
:deep(.form-control select),
:deep(.form-control textarea),
:deep(.form-control button) {
  border-color: transparent;
  background: white;
}

:deep(.form-control button) {
  gap: 0;
}
:deep(.form-control [type="checkbox"]) {
  margin-left: 9px;
  cursor: pointer;
}

:deep(.form-control button > div) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

:deep(.form-control button svg) {
  color: white;
  width: 0;
}
</style>
