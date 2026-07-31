// Browser notifications are reinforcement only: they fire while the tab is
// alive and permission was already granted. The correctness of the recorded
// time never depends on them (the server closes expired sessions lazily).

export function requestNotificationPermission(): void {
  if ('Notification' in window && Notification.permission === 'default') {
    void Notification.requestPermission()
  }
}

export function notify(title: string, body: string): void {
  if (!('Notification' in window) || Notification.permission !== 'granted') return
  try {
    new Notification(title, { body })
  } catch {
    // Some platforms refuse page-created notifications; reinforcement only.
  }
}
