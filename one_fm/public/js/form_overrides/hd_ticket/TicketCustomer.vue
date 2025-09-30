<template>
  <div v-if="ticket.data" class="flex flex-col">
    <LayoutHeader>
      <template #left-header>
        <Breadcrumbs :items="breadcrumbs" />
      </template>
      <template #right-header>
        <CustomActions
          v-if="ticket.data._customActions"
          :actions="ticket.data._customActions"
        />
        <Button
          v-if="ticket.data.status === 'Resolved'"
          label="Reopen"
          theme="blue"
          variant="solid"
          @click="handleReopen()"
        >
          <template #prefix>
            <Icon icon="lucide:rotate-ccw" />
          </template>
        </Button>
        <Button
          v-if="ticket.data.status !== 'Closed'"
          label="Close"
          theme="gray"
          variant="solid"
          @click="handleClose()"
        >
          <template #prefix>
            <Icon icon="lucide:check" />
          </template>
        </Button>

      </template>
    </LayoutHeader>
    <div class="flex overflow-hidden h-full w-full">
      <!-- Main Ticket Comm -->
      <section class="flex flex-col flex-1 w-full md:max-w-[calc(100%-382px)]">
        <!-- show for only mobile -->
        <TicketCustomerTemplateFields v-if="isMobileView" />

        <TicketConversation class="grow" />
        <div
          class="w-full p-5"
          @keydown.ctrl.enter.capture.stop="sendEmail"
          @keydown.meta.enter.capture.stop="sendEmail"
        >
          <TicketTextEditor
            v-if="showEditor"
            ref="editor"
            v-model:attachments="attachments"
            v-model:content="editorContent"
            v-model:expand="isExpanded"
            placeholder="Type a message"
            autofocus
            @clear="() => (isExpanded = false)"
            :uploadFunction="(file:any)=>uploadFunction(file, 'HD Ticket', props.ticketId)"
          >
            <template #bottom-right>
              <Button
                label="Send"
                theme="gray"
                variant="solid"
                :disabled="$refs.editor?.editor.isEmpty || send.loading"
                :loading="send.loading"
                @click="sendEmail"
              />
            </template>
          </TicketTextEditor>
        </div>
      </section>
      <!-- Ticket Sidebar only for desktop view-->
      <TicketCustomerSidebar v-if="!isMobileView" @open="isExpanded = true" />
    </div>
    <TicketFeedback v-model:open="showFeedbackDialog" />
    
    <Dialog v-model="showTicketFeedbackDialog">
      <template #body-title>
        <h3>{{ feedbackAction === 'close' ? 'Close Ticket Feedback' : 'Reopen Ticket Feedback' }}</h3>
      </template>
      
      <template #body-content>
        <div class="mb-4">
          <p class="text-gray-600 mb-4">
            {{ feedbackAction === 'close' 
              ? 'Please provide feedback on the ticket resolution:' 
              : 'Please provide feedback on why you are reopening this ticket:' 
            }}
          </p>
          <TextEditor 
            v-model="feedbackText"
            :placeholder="feedbackAction === 'close' 
              ? 'Please provide your feedback on how the ticket was resolved...' 
              : 'Please describe the issues that need attention...'"
            editor-class="min-h-[120px] max-h-60"
            @change="(val) => feedbackText = val"
          />
        </div>
      </template>
      
      <template #actions>
        <div class="flex justify-between w-full">
          <Button @click="closeFeedbackDialog">Cancel</Button>
          <Button 
            variant="solid" 
            :theme="feedbackAction === 'close' ? 'gray' : 'blue'"
            @click="submitFeedback"
            :loading="submitFeedbackResource.loading"
          >
            {{ feedbackAction === 'close' ? 'Close Ticket' : 'Reopen Ticket' }}
          </Button>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { LayoutHeader } from "@/components";
import TicketCustomerSidebar from "@/components/ticket/TicketCustomerSidebar.vue";
import { setupCustomizations } from "@/composables/formCustomisation";
import { useScreenSize } from "@/composables/screen";
import { socket } from "@/socket";
import { useConfigStore } from "@/stores/config";
import { globalStore } from "@/stores/globalStore";
import { isContentEmpty, uploadFunction } from "@/utils";
import { Icon } from "@iconify/vue";
import { Breadcrumbs, Button, call, createResource, toast, TextEditor, Dialog } from "frappe-ui";
import { computed, onMounted, onUnmounted, provide, ref } from "vue";
import { useRouter } from "vue-router";
import { useTicket } from "./data";
import { ITicket } from "./symbols";
import TicketCustomerTemplateFields from "./TicketCustomerTemplateFields.vue";
import TicketConversation from "./TicketConversation.vue";
import TicketFeedback from "./TicketFeedback.vue";
import TicketTextEditor from "./TicketTextEditor.vue";

interface P {
  ticketId: string;
}
const router = useRouter();

const props = defineProps<P>();
const ticket = useTicket(
  props.ticketId,
  true,
  null,
  (data) => {
    setupCustomizations(ticket, {
      doc: data,
      call,
      router,
      toast,
      $dialog,
      updateField,
      createToast: toast.create,
    });
  },
  () => {
    toast.error("Ticket not found");
    router.replace("/my-tickets");
  }
);
provide(ITicket, ticket);

const editor = ref(null);
const editorContent = ref("");
const attachments = ref([]);
const showFeedbackDialog = ref(false);
const showTicketFeedbackDialog = ref(false);
const feedbackText = ref('');
const feedbackAction = ref('');
const isExpanded = ref(false);

const { isMobileView } = useScreenSize();
const { $dialog } = globalStore();

const send = createResource({
  url: "run_doc_method",
  debounce: 300,
  makeParams: () => ({
    dt: "HD Ticket",
    dn: props.ticketId,
    method: "create_communication_via_contact",
    args: {
      message: editorContent.value,
      attachments: attachments.value,
    },
  }),
  onSuccess: () => {
    editor.value.editor.commands.clearContent(true);
    attachments.value = [];
    isExpanded.value = false;
    ticket.reload();
  },
});

const submitFeedbackResource = createResource({
  url: "one_fm.overrides.hd_ticket.update_ticket_with_feedback",
  makeParams: () => ({
    ticket_id: props.ticketId,
    feedback: feedbackText.value,
    action: feedbackAction.value,
  }),
  onSuccess: (data) => {
    if (data.success) {
      toast.success(data.message);
      ticket.reload();
      closeFeedbackDialog();
    } else {
      toast.error(data.message);
    }
  },
  onError: () => {
    toast.error("Failed to update ticket. Please try again.");
  }
});

function updateField(name, value, callback = () => {}) {
  updateTicket(name, value);
  callback();
}

function sendEmail() {
  if (isContentEmpty(editorContent.value) || send.loading) {
    return;
  }
  send.submit();
}

function updateTicket(fieldname: string, value: string) {
  createResource({
    url: "frappe.client.set_value",
    params: {
      doctype: "HD Ticket",
      name: props.ticketId,
      fieldname,
      value,
    },
    auto: true,
    onSuccess: () => {
      ticket.reload();
      toast.success("Ticket updated");
    },
  });
}

function handleClose() {
  if (showFeedback.value) {
    showFeedbackDialog.value = true;
  } else {
    showCloseConfirmationDialog();
  }
}

function handleReopen() {
  showReopenConfirmationDialog();
}

function showCloseConfirmationDialog() {
  $dialog({
    title: "Close Ticket",
    message: "Are you sure you want to close this ticket?",
    actions: [
      {
        label: "Confirm",
        variant: "solid",
        onClick(close: Function) {
          feedbackAction.value = "close";
          showTicketFeedbackDialog.value = true;
          close();
        },
      },
    ],
  });
}

function showReopenConfirmationDialog() {
  $dialog({
    title: "Reopen Ticket", 
    message: "Are you sure you want to reopen this ticket?",
    actions: [
      {
        label: "Confirm",
        variant: "solid",
        theme: "blue",
        onClick(close: Function) {
          feedbackAction.value = "reopen";
          showTicketFeedbackDialog.value = true;
          close();
        },
      },
    ],
  });
}

function submitFeedback() {
  console.log('Feedback text:', feedbackText.value);
  console.log('Feedback action:', feedbackAction.value);
  
  if (!feedbackText.value || !feedbackText.value.trim()) {
    toast.warning("Please provide feedback before proceeding");
    return;
  }
  submitFeedbackResource.submit();
}

function closeFeedbackDialog() {
  showTicketFeedbackDialog.value = false;
  feedbackText.value = '';
  feedbackAction.value = '';
}

function showConfirmationDialog() {
  $dialog({
    title: "Close Ticket",
    message: "Are you sure you want to close this ticket?",
    actions: [
      {
        label: "Confirm",
        variant: "solid",
        onClick(close: Function) {
          ticket.data.status = "Closed";
          setValue.submit(
            { fieldname: "status", value: "Closed" },
            {
              onSuccess: () => {
                toast.success("Ticket closed");
              },
            }
          );
          close();
        },
      },
    ],
  });
}

const setValue = createResource({
  url: "frappe.client.set_value",
  debounce: 300,
  makeParams: (params) => {
    return {
      doctype: "HD Ticket",
      name: props.ticketId,
      fieldname: params.fieldname,
      value: params.value,
    };
  },
  onSuccess: () => {
    showFeedbackDialog.value = false;
    ticket.reload();
  },
});

const breadcrumbs = computed(() => {
  let items = [{ label: "Tickets", route: { name: "TicketsCustomer" } }];
  items.push({
    label: ticket.data?.subject,
    route: { name: "TicketCustomer" },
  });
  return items;
});

const showEditor = computed(() => ticket.data.status !== "Closed");

const { isFeedbackMandatory } = useConfigStore();
const showFeedback = computed(() => {
  const hasAgentCommunication = ticket.data?.communications?.some(
    (c) => c.sender !== ticket.data.raised_by
  );
  return hasAgentCommunication && isFeedbackMandatory;
});

onMounted(() => {
  document.title = props.ticketId;
  socket.on("helpdesk:ticket-update", (ticketID) => {
    if (ticketID === Number(props.ticketId)) {
      ticket.reload();
    }
  });
});

onUnmounted(() => {
  document.title = "Helpdesk";
  socket.off("helpdesk:ticket-update");
});
</script>