<template>
  <LayoutHeader>
    <template #left-header>
      <div class="flex flex-col truncate">
        <Breadcrumbs :items="breadcrumbs" class="breadcrumbs -ml-0.5">
          <template #prefix="{ item }">
            <Icon
              v-if="item.icon"
              :icon="item.icon"
              class="mr-1 h-4 flex items-center justify-center self-center"
            />
          </template>
        </Breadcrumbs>
        <TicketSLA />
      </div>
    </template>
    <template #right-header>
      <div class="flex gap-2 items-center">
        <MultipleAvatar
          :avatars="JSON.stringify(viewers)"
          size="md"
          :hide-name="true"
        />
        <!-- Navigation -->
        <TicketNavigation :key="ticket?.name" />
        <!-- Custom Actions -->
        <div v-if="normalActions.length" class="flex gap-2">
          <Button v-for="action in normalActions" v-bind="action">
            <template v-if="action.icon" #prefix>
              <FeatherIcon :name="action.icon" class="h-4 w-4" />
            </template>
          </Button>
        </div>
        <div v-if="groupedWithLabelActions.length">
          <div v-for="g in groupedWithLabelActions" :key="g.label">
            <Dropdown v-slot="{ open }" :options="g.action">
              <Button :label="g.label">
                <template #suffix>
                  <FeatherIcon
                    :name="open ? 'chevron-up' : 'chevron-down'"
                    class="h-4"
                  />
                </template>
              </Button>
            </Dropdown>
          </div>
        </div>
        <!-- BPMN Actions — dropdown shown when a BPMN process controls this ticket -->
        <Dropdown
          v-if="bpmnActions.length"
          :options="bpmnDropdownOptions"
          placement="right"
        >
          <template #default>
            <Button :label="ticket.doc.status">
              <template #prefix>
                <IndicatorIcon
                  :class="
                    ticketStatusStore.getStatus(ticket.doc.status)?.parsed_color
                  "
                />
              </template>
              <template #suffix>
                <FeatherIcon name="chevron-down" class="h-4" />
              </template>
            </Button>
          </template>
        </Dropdown>
        <!-- BPMN process active but no action assigned to current user -->
        <Button
          v-else-if="hasBpmnControl"
          :label="ticket.doc.status"
          :disabled="true"
        >
          <template #prefix>
            <IndicatorIcon
              :class="
                ticketStatusStore.getStatus(ticket.doc.status)?.parsed_color
              "
            />
          </template>
        </Button>
        <!-- Status (native) — only when no BPMN process controls this ticket -->
        <Dropdown v-else :options="statusDropdown" placement="right">
          <template #default="{ open }">
            <Button :label="ticket.doc.status" ref="statusRef">
              <template #prefix>
                <IndicatorIcon
                  :class="
                    ticketStatusStore.getStatus(ticket.doc.status)?.parsed_color
                  "
                />
              </template>
            </Button>
          </template>
        </Dropdown>
        <!-- Core Actions + Custom Actions -->
        <Dropdown
          v-if="groupedActions[0]?.items?.length >= 1"
          :options="groupedActions"
          placement="right"
        >
          <Button icon="more-horizontal" />
        </Dropdown>
      </div>
    </template>
  </LayoutHeader>
  <TicketMergeModal
    :ticket="ticket.doc"
    v-if="showMergeModal"
    v-model="showMergeModal"
    @update="ticket.reload()"
  />
  <TicketSubjectModal v-model="showSubjectDialog" />
</template>

<script setup lang="ts">
import { MultipleAvatar } from "@/components";
import LayoutHeader from "@/components/LayoutHeader.vue";
import TicketMergeModal from "@/components/ticket/TicketMergeModal.vue";
import { setupCustomizations } from "@/composables/formCustomisation";
import { useNotifyTicketUpdate } from "@/composables/realtime";
import { useShortcut } from "@/composables/shortcuts";
import { useView } from "@/composables/useView";
import { useAuthStore } from "@/stores/auth";
import { globalStore } from "@/stores/globalStore";
import { useTicketStatusStore } from "@/stores/ticketStatus";
import { __ } from "@/translation";
import {
  ActivitiesSymbol,
  CustomizationSymbol,
  TicketSymbol,
  View,
} from "@/types";
import { HDTicketStatus } from "@/types/doctypes";
import { getIcon, parseColor } from "@/utils";
import {
  Breadcrumbs,
  Button,
  call,
  createResource,
  Dropdown,
  toast,
} from "frappe-ui";
import {
  computed,
  ComputedRef,
  h,
  inject,
  onMounted,
  onUnmounted,
  PropType,
  ref,
  useTemplateRef,
  watch,
  watchEffect,
} from "vue";
import { useRoute, useRouter } from "vue-router";
import LucideMerge from "~icons/lucide/merge";
import { IndicatorIcon } from "../icons";
import TicketNavigation from "./TicketNavigation.vue";
import TicketSLA from "./TicketSLA.vue";
import TicketSubjectModal from "./TicketSubjectModal.vue";
const authStore = useAuthStore();
const { isAdmin } = authStore;
const { $dialog, $socket } = globalStore();

defineProps({
  viewers: {
    type: Array as PropType<string[]>,
    required: true,
  },
});

const route = useRoute();
const router = useRouter();
const { findView } = useView("HD Ticket");
const ticketStatusStore = useTicketStatusStore();

const ticket = inject(TicketSymbol)!;
const customizations = inject(CustomizationSymbol)!;
const activities = inject(ActivitiesSymbol)!;
const showSubjectDialog = ref(false);

const { notifyTicketUpdate } = useNotifyTicketUpdate(ticket.value?.name);

/* ──────────────────────────────────────────────────────────────────────────
 * BPMN Process Actions
 *
 * When a BPMN Process Instance controls this HD Ticket, we replace the native
 * Status dropdown with the BPMN User Task action buttons (mirrors the Frappe
 * Desk injector in one_bpmn/public/js/bpmn_form_actions.js).
 * ──────────────────────────────────────────────────────────────────────── */
const bpmnTasks = ref<any[]>([]);

// Any active BPMN process controls this ticket → hide the native Status dropdown.
const hasBpmnControl = computed(() => bpmnTasks.value.length > 0);

// Action buttons the current user is allowed to act on.
const bpmnActions = computed(() => {
  const currentUser = authStore.user;
  const ownerIsMe = ticket.value?.doc?.owner === currentUser;
  const buttons: Array<{
    label: string;
    color: string;
    task: any;
    detail: any;
  }> = [];

  bpmnTasks.value.forEach((task) => {
    const isForMe =
      !task.assigned_user ||
      task.assigned_user === currentUser ||
      ownerIsMe;
    if (!isForMe) return;

    const details = getBpmnActionDetails(task);
    if (details.length) {
      details.forEach((d: any) => {
        buttons.push({
          label: __(d.action),
          color: bpmnActionColor(d.action),
          task,
          detail: d,
        });
      });
    } else {
      buttons.push({
        label: __(task.task_name || "Complete Task"),
        color: parseColor("gray"),
        task,
        detail: null,
      });
    }
  });

  return buttons;
});

// Dropdown options (mirrors statusDropdown) — each action becomes a menu item
// with a coloured indicator, shown under a single Status-style trigger button.
const bpmnDropdownOptions = computed(() =>
  bpmnActions.value.map((btn) => ({
    label: btn.label,
    icon: () => h(IndicatorIcon, { class: btn.color }),
    onClick: () => handleBpmnAction(btn),
  }))
);

// Map a BPMN action to a status-palette colour, so the buttons match the
// coloured Status indicators used elsewhere in the portal.
function bpmnActionColor(action: string): string {
  const a = (action || "").toLowerCase();
  let color = "blue";
  if (/(resolve|resolved|approve|complete|close|reviewed|done)/.test(a)) {
    color = "green";
  } else if (/(reject|return|cancel|decline|escalat)/.test(a)) {
    color = "red";
  } else if (/(pending|deploy|hold|wait)/.test(a)) {
    color = "orange";
  } else if (/(work item|assign|create|add)/.test(a)) {
    color = "violet";
  } else if (/(repl|respond|comment)/.test(a)) {
    color = "blue";
  }
  return parseColor(color);
}

// Extract structured action details (mirrors bpmn_form_actions.js).
function getBpmnActionDetails(task: any): any[] {
  if (Array.isArray(task.task_actions_detail) && task.task_actions_detail.length) {
    return task.task_actions_detail.filter((d: any) => d && d.action);
  }
  const raw = (task.task_actions || "").trim();
  if (!raw) return [];
  if (raw.startsWith("[")) {
    try {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return parsed.filter((d: any) => d && d.action);
    } catch (_) {
      /* fall through to CSV */
    }
  }
  return raw
    .split(",")
    .map((a: string) => a.trim())
    .filter(Boolean)
    .map((a: string) => ({ action: a }));
}

async function loadBpmnActions() {
  const docname = ticket.value?.doc?.name;
  if (!docname) {
    bpmnTasks.value = [];
    return;
  }
  try {
    const tasks = await call(
      "one_bpmn.api.instance_api.get_active_bpmn_tasks",
      { doctype: "HD Ticket", docname }
    );
    bpmnTasks.value = Array.isArray(tasks) ? tasks : [];
  } catch (e) {
    bpmnTasks.value = [];
  }
}

function handleBpmnAction(btn: { label: string; task: any; detail: any }) {
  const { task, detail } = btn;
  const action = detail ? detail.action : null;
  const needsConfirm = detail ? detail.confirmTransition === "true" : true;

  const apply = () => applyBpmnAction(task, action);

  if (needsConfirm) {
    $dialog({
      title: __("Confirm Action"),
      message: action
        ? __("Apply action '{0}' on this ticket?", action)
        : __("Complete task '{0}'?", task.task_name || "Task"),
      actions: [
        {
          label: __("Confirm"),
          variant: "solid",
          onClick: ({ close }: { close: () => void }) => {
            apply();
            close();
          },
        },
      ],
    });
  } else {
    apply();
  }
}

function applyBpmnAction(task: any, action: string | null) {
  call("one_bpmn.api.instance_api.complete_task", {
    instance_name: task.instance_name,
    task_id: task.task_id,
    data: action ? JSON.stringify({ action }) : "{}",
  })
    .then(() => {
      toast.success(
        __("{0} applied successfully", action || task.task_name || "Action")
      );
      ticket.value.reload();
      activities.value.reload();
      loadBpmnActions();
    })
    .catch((err: any) => {
      const msg =
        (err && (err.messages?.join(", ") || err.message)) ||
        __("Failed to apply action.");
      toast.error(msg);
    });
}

const statusDropdown = computed(() => {
  const statuses =
    ticketStatusStore.statuses.data?.filter((s) => s.enabled) || [];
  return statuses.map((o: HDTicketStatus) => ({
    label: o.label_agent,
    value: o.label_agent,
    onClick: () => {
      notifyTicketUpdate("Status", o.label_agent);
      if (ticket.value.doc.status === o.label_agent) return;
      ticket.value.setValue.submit(
        { status: o.label_agent },
        {
          onSuccess() {
            activities.value.reload();
          },
        }
      );
    },
    icon: () =>
      h(IndicatorIcon, {
        class: o.parsed_color,
      }),
  }));
});
const breadcrumbs = computed(() => {
  let items = [{ label: __("Tickets"), route: { name: "TicketsAgent" } }];
  if (route.query.view) {
    const currView: ComputedRef<View> = findView(route.query.view as string);
    if (currView) {
      items.push({
        label: currView.value?.label,
        icon: getIcon(currView.value?.icon),
        route: { name: "TicketsAgent", query: { view: currView.value?.name } },
      });
    }
  }
  items.push({
    label: ticket.value.doc?.subject,
    onClick: () => {
      showSubjectDialog.value = true;
    },
  });
  return items;
});

function updateField(fieldname: string, value: string, callback = () => {}) {
  const doc = ticket.value;
  doc.setValue.submit({
    [fieldname]: value,
  });
  callback();
}

function handleDeleteTicket() {
  $dialog({
    title: __(`Delete ticket #${ticket?.value?.name}`),
    message: __(
      "Are you sure you want to delete this ticket? This is an irreversible action and cannot be undone."
    ),
    actions: [
      {
        label: __("Delete"),
        theme: "red",
        iconLeft: "trash-2",
        variant: "solid",
        onClick({ close }) {
          call("frappe.client.delete", {
            doctype: "HD Ticket",
            name: ticket?.value?.doc.name,
          })
            .then(() => {
              toast.success(__("Ticket deleted successfully."));
              router.push({ name: "TicketsAgent" });
            })
            .catch((err: any) => {
              toast.error(err || __("Failed to delete ticket."));
            });
          close();
        },
      },
    ],
  });
}

const ticketCount = createResource({
  url: "frappe.client.get_count",
  makeParams: () => ({
    doctype: "HD Ticket",
    filters: {
      status_category: ["!=", "Resolved"],
      is_merged: 0,
    },
  }),
  auto: true,
});
const showMergeModal = ref(false);
const showMergeOption = computed(() => {
  return (
    !ticket?.value?.doc?.is_merged &&
    ["Open", "Paused"].includes(ticket?.value?.doc?.status_category) &&
    ticketCount.data > 1
  );
});
const defaultActions = computed(() => {
  let items = [];

  if (showMergeOption.value) {
    items.push({
      label: __("Merge Ticket"),
      icon: LucideMerge,
      condition: () => !ticket.value.doc.is_merged,
      onClick: () => (showMergeModal.value = true),
    });
  }

  return [
    {
      group: __("Default actions"),
      hideLabel: true,
      items,
    },
  ];
});

const deleteAction = computed(() => {
  if (!isAdmin) return [];
  return [
    {
      group: __("Default actions"),
      hideLabel: true,
      items: [
        {
          label: __("Delete"),
          component: h(Button, {
            label: __("Delete"),
            variant: "ghost",
            iconLeft: "trash-2",
            theme: "red",
            style: "width: 100%; justify-content: flex-start;",
            onClick: handleDeleteTicket,
          }),
        },
      ],
    },
  ];
});

const actions = ref<any[]>([]);
const normalActions = computed(() => {
  return actions.value.filter((action) => !action.group);
});

const groupedWithLabelActions = computed(() => {
  let _actions = [];

  actions.value
    .filter((action) => action.buttonLabel && action.group)
    .forEach((action) => {
      let groupIndex = _actions.findIndex(
        (a) => a.label === action.buttonLabel
      );
      if (groupIndex > -1) {
        _actions[groupIndex].action.push(action);
      } else {
        _actions.push({
          label: action.buttonLabel,
          action: [action],
        });
      }
    });
  return _actions;
});

const groupedActions = computed(() => {
  let _actions = [];
  _actions = _actions.concat(defaultActions.value);
  _actions = _actions.concat(
    actions.value.filter((action) => action.group && !action.buttonLabel)
  );
  _actions = _actions.concat(deleteAction.value);
  return _actions;
});

const customizationCtx = computed(() => ({
  doc: ticket?.value?.doc,
  call,
  router,
  toast,
  $dialog: globalStore().$dialog,
  updateField,
  createToast: toast.create,
}));

// to manage the correct  customization context for actions, happens because of navigation between tickets using buttons
watchEffect(async () => {
  if (customizations.value?.data) {
    await setupCustomizations(
      customizations.value.data,
      customizationCtx.value
    );

    actions.value = [...(customizations.value?.data?._customActions || [])];
  }
});

const statusRef = useTemplateRef("statusRef");

// Reload BPMN actions when the open ticket changes (navigation between tickets).
watch(
  () => ticket.value?.doc?.name,
  () => loadBpmnActions(),
  { immediate: true }
);

// Realtime: refresh actions when a BPMN task completes elsewhere (Processa / another user).
function onBpmnInstanceUpdated(data: any) {
  const docname = ticket.value?.doc?.name;
  if (!docname) return;
  if (
    data?.context_doctype &&
    data?.context_docname &&
    (data.context_doctype !== "HD Ticket" || data.context_docname !== docname)
  ) {
    return;
  }
  ticket.value.reload();
  loadBpmnActions();
}

onMounted(() => {
  useShortcut("s", () => {
    statusRef.value?.$el?.nextElementSibling?.click();
  });
  $socket?.on("bpmn_instance_updated", onBpmnInstanceUpdated);
});

onUnmounted(() => {
  $socket?.off("bpmn_instance_updated", onBpmnInstanceUpdated);
});
</script>

<style>
.breadcrumbs button {
  background-color: inherit !important;
  &:hover,
  &:focus {
    background-color: inherit !important;
  }
}
</style>
