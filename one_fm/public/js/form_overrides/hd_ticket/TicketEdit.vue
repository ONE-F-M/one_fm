<template>
  <div class="flex h-screen overflow-hidden">

    <!-- Main content -->
    <div class="flex flex-col flex-1 h-full overflow-hidden">
      <!-- Header -->
      <header class="flex h-10.5 items-center justify-between mx-4 md:mr-0">
        <div class="flex items-center gap-2 max-w-[50%]">
          <div class="flex min-w-0 items-center">
            <div class="flex min-w-0 items-center overflow-hidden text-ellipsis whitespace-nowrap">
              <RouterLink
                to="/helpdesk/my-tickets"
                class="flex items-center rounded px-0.5 py-1 text-lg font-medium focus:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3 text-ink-gray-5 hover:text-ink-gray-7"
              >
                <span>Tickets</span>
              </RouterLink>
              <span class="mx-0.5 text-base text-ink-gray-4" aria-hidden="true"> / </span>
              <span
                class="flex items-center rounded px-0.5 py-1 text-lg font-medium text-ink-gray-9"
              >
                Edit Ticket
              </span>
            </div>
          </div>
        </div>
        <div class="flex items-center gap-2"></div>
      </header>

      <div class="flex flex-col gap-5 py-6 overflow-auto mx-auto w-full max-w-4xl px-5">

      <div
        class="grid grid-cols-1 gap-4 sm:grid-cols-3"
        v-if="filteredFields.length"
      >
        <div
          class="space-y-1.5"
          v-for="field in filteredFields"
        >
          <UniInput
            :field="field"
            :value="templateFields[field.fieldname]"
            @change="(e) => handleOnFieldChange(e, field.fieldname, field.fieldtype)"
          />
        </div>
      </div>


        <!-- Subject -->
        <div class="flex flex-col gap-2">
          <span class="block text-sm text-gray-700">
            Subject <span class="text-red-500">*</span>
          </span>
          <FormControl v-model="subject" type="text" placeholder="A short description" />
        </div>

        <!-- Description -->
        <TicketTextEditor
          ref="editor"
          v-model:attachments="attachments"
          v-model:content="description"
          placeholder="Detailed explanation"
          expand
        >
          <template #bottom-right>
            <Button
              label="Update Ticket"
              theme="gray"
              variant="solid"
              :disabled="$refs.editor?.editor?.isEmpty || loading || !subject"
              @click="handleSubmit"
            />
          </template>
        </TicketTextEditor>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { useRoute, useRouter, RouterLink } from "vue-router";
import { call, Button, FormControl, createResource } from "frappe-ui";
import { usePageMeta } from "frappe-ui";
import { globalStore } from "@/stores/globalStore";
import { LayoutHeader, UniInput } from "@/components";
import Sidebar from "@/components/layouts/Sidebar.vue";
import TicketTextEditor from "./TicketTextEditor.vue";
import {
  parseField,
  setupCustomizations,
  handleSelectFieldUpdate,
  handleLinkFieldUpdate,
} from "@/composables/formCustomisation";

const route = useRoute();
const router = useRouter();
const ticketName = route.params.ticket_name as string;

const subject = ref("");
const description = ref("");
const attachments = ref([]);
const loading = ref(false);
const templateFields = reactive({});
const { $dialog } = globalStore();

const priorities = ref<string[]>([]);
const processes = ref<string[]>([]);

async function fetchOptions(endpoint: string, targetRef: typeof ref<string[]>) {
  try {
    const res = await call(endpoint);
    if (res.status_code === 200) {
      targetRef.value = res.data;
    }
  } catch (e) {
    console.error(`Failed to fetch ${endpoint}`, e);
  }
}

const templateData = ref<any>({ fields: [] });
let oldFields = [];

const visibleFields = computed(() =>
  templateData.value.fields.map((field) => {
    if (Array.isArray(field.options)) {
      field.options = field.options.join("\n");
    }
    return parseField(field, templateFields);
  })
);

const filteredFields = computed(() =>
  visibleFields.value
);

function applyFilters(fieldname, filters = null) {
  const field = templateData.value?.fields?.find((f) => f.fieldname === fieldname);
  if (!field) {
    console.warn(`Field '${fieldname}' not found in templateData`);
    return;
  }

  if (field.fieldtype === "Select") {
    if (fieldname === "priority") {
      field.options = priorities.value;
    } else if (fieldname === "process") {
      field.options = processes.value;
    }
    handleSelectFieldUpdate(field, fieldname, filters, templateFields, oldFields);
  } else if (field.fieldtype === "Link") {
    handleLinkFieldUpdate(field, fieldname, filters, templateFields, oldFields);
  }
}

function handleOnFieldChange(e, fieldname, fieldtype) {
  templateFields[fieldname] = e.value;
}

// Create a resource to fetch the template using the Frappe API
const templateResource = createResource({
  url: "helpdesk.helpdesk.doctype.hd_ticket_template.api.get_one",
  makeParams: () => ({
    name: "Default", // We'll update this after fetching the ticket's template
  }),
  auto: false,
});

async function fetchTicketDetails() {
  if (!ticketName) return;

  try {
    const res = await call("one_fm.overrides.hd_ticket.get_ticket_details", {
      name: ticketName,
    });
    const data = res.data;

    subject.value = data.subject || "";
    description.value = data.description || "";

    // Fetch template using the template name from ticket
    const templateName = "Default";
    
    const templateRes = await call("helpdesk.helpdesk.doctype.hd_ticket_template.api.get_one", {
      name: templateName,
    });
    
    if (templateRes && templateRes.fields && templateRes.fields.length) {
      templateData.value.fields = templateRes.fields;
      oldFields = JSON.parse(JSON.stringify(templateRes.fields));
    }

    for (const field of templateData.value.fields) {
      const key = field.fieldname;
      // Try to get custom field value from ticket document
      const customKey = key.startsWith("custom_") ? key : `custom_${key}`;
      const value = data[customKey] || data[key] || "";
      templateFields[key] = value;
    }

    setupCustomizations(templateData, {
      doc: templateFields,
      call,
      router,
      $dialog,
      applyFilters,
    });

  } catch (e) {
    console.error("Failed to fetch ticket", e);
  }
}


async function handleSubmit() {
  loading.value = true;
  try {
    await call("one_fm.overrides.hd_ticket.update_ticket", {
      name: ticketName,
      updates: JSON.stringify({
        subject: subject.value,
        description: description.value,
        ...templateFields
      }),
    });
    router.push("/");
  } catch (e) {
    console.error("Failed to update ticket", e);
  } finally {
    loading.value = false;
  }
}

usePageMeta(() => ({ title: "Edit Ticket" }));

function injectFallbackFields() {
  if (!templateData.value.fields || templateData.value.fields.length === 0) {
    templateData.value.fields = [
      {
        label: "Priority",
        fieldname: "priority",
        fieldtype: "Select",
        options: priorities.value,
        reqd: 1,
      },
      {
        label: "Process",
        fieldname: "process",
        fieldtype: "Select",
        options: processes.value,
        reqd: 1,
      },
    ];
  }
}

onMounted(async () => {
  await fetchOptions("one_fm.overrides.hd_ticket.get_priority", priorities);
  await fetchOptions("one_fm.overrides.hd_ticket.get_process", processes);

  await fetchTicketDetails();

  // Only inject fallback fields if no fields were loaded from the template
  if (!templateData.value.fields || templateData.value.fields.length === 0) {
    injectFallbackFields();
  }
  // applyFilters("priority");
  // applyFilters("process");
});

</script>
