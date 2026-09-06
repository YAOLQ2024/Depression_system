export type SystemNotificationTone = "error";

export type SystemNotification = {
  id: string;
  message: string;
  tone: SystemNotificationTone;
  createdAt: number;
  read: boolean;
};

type NotificationListener = () => void;

let notifications: SystemNotification[] = [];
const listeners = new Set<NotificationListener>();

function emitChange() {
  listeners.forEach((listener) => listener());
}

/** Stores runtime errors independently of temporary toast visibility. */
export function reportSystemError(message: string) {
  const normalizedMessage = message.trim();
  if (!normalizedMessage) return;

  const now = Date.now();
  const latest = notifications[0];
  if (latest?.message === normalizedMessage && now - latest.createdAt < 3_000) {
    notifications = [{ ...latest, createdAt: now, read: false }, ...notifications.slice(1)];
  } else {
    const notification: SystemNotification = {
      id: `${now}-${Math.random().toString(36).slice(2, 8)}`,
      message: normalizedMessage,
      tone: "error",
      createdAt: now,
      read: false,
    };
    notifications = [notification, ...notifications].slice(0, 50);
  }
  emitChange();
}

export function getSystemNotifications() {
  return notifications;
}

export function markSystemNotificationsRead() {
  if (!notifications.some((notification) => !notification.read)) return;
  notifications = notifications.map((notification) => ({ ...notification, read: true }));
  emitChange();
}

export function subscribeSystemNotifications(listener: NotificationListener) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
