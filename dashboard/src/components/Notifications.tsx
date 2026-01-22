import { useState, useEffect, useCallback } from 'react';
import { Bell, BellOff, CheckCircle2, XCircle, AlertCircle, Info } from 'lucide-react';
import clsx from 'clsx';
import { formatDistanceToNow } from 'date-fns';
import toast from 'react-hot-toast';

interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message?: string;
  timestamp: string;
  read: boolean;
  modeId?: string;
  actionLabel?: string;
  actionUrl?: string;
}

// Mock notifications
const mockNotifications: Notification[] = [
  {
    id: '1',
    type: 'success',
    title: 'Mode 2 completed',
    message: 'Feasibility assessment finished with GO verdict',
    timestamp: new Date(Date.now() - 300000).toISOString(),
    read: false,
    modeId: '2',
  },
  {
    id: '2',
    type: 'error',
    title: 'Mode 3 failed',
    message: 'Strategy generation encountered an error',
    timestamp: new Date(Date.now() - 600000).toISOString(),
    read: false,
    modeId: '3',
    actionLabel: 'View Error',
  },
  {
    id: '3',
    type: 'info',
    title: 'New artifact available',
    message: 'FeasibilityReport created from Mode 2',
    timestamp: new Date(Date.now() - 900000).toISOString(),
    read: true,
  },
];

export function NotificationCenter() {
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>(mockNotifications);
  const [notifyOnComplete, setNotifyOnComplete] = useState<Set<string>>(new Set());

  const unreadCount = notifications.filter((n) => !n.read).length;

  const markAsRead = (id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
  };

  const markAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  const clearAll = () => {
    setNotifications([]);
    setIsOpen(false);
  };

  const toggleNotifyOnComplete = (modeId: string) => {
    setNotifyOnComplete((prev) => {
      const next = new Set(prev);
      if (next.has(modeId)) {
        next.delete(modeId);
        toast.success(`Notifications disabled for Mode ${modeId}`);
      } else {
        next.add(modeId);
        toast.success(`You'll be notified when Mode ${modeId} completes`);
      }
      return next;
    });
  };

  // Request browser notification permission
  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, []);

  // Browser notification support (available for future use)
  useCallback((notification: Notification) => {
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification(notification.title, {
        body: notification.message,
        icon: '/meridian.svg',
        tag: notification.id,
      });
    }
  }, []);

  return (
    <div className="relative">
      {/* Bell Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="btn btn-icon btn-ghost relative"
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 w-5 h-5 flex items-center justify-center text-2xs font-medium bg-status-error text-white rounded-full">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />

          {/* Panel */}
          <div className="absolute right-0 top-full mt-2 w-96 bg-bg-secondary border border-border rounded-xl shadow-2xl z-50 overflow-hidden animate-fade-in">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-border-subtle">
              <h3 className="font-semibold">Notifications</h3>
              <div className="flex items-center gap-2">
                {unreadCount > 0 && (
                  <button
                    onClick={markAllAsRead}
                    className="text-xs text-accent-blue hover:underline"
                  >
                    Mark all read
                  </button>
                )}
                <button
                  onClick={clearAll}
                  className="text-xs text-text-muted hover:text-text-secondary"
                >
                  Clear all
                </button>
              </div>
            </div>

            {/* Notification List */}
            <div className="max-h-96 overflow-y-auto">
              {notifications.length === 0 ? (
                <div className="p-8 text-center text-text-muted">
                  <BellOff className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No notifications</p>
                </div>
              ) : (
                <div className="divide-y divide-border-subtle">
                  {notifications.map((notification) => (
                    <NotificationItem
                      key={notification.id}
                      notification={notification}
                      onRead={() => markAsRead(notification.id)}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Footer - Notification Settings */}
            <div className="px-4 py-3 border-t border-border-subtle bg-bg-tertiary">
              <div className="text-xs text-text-muted mb-2">Notify me when complete:</div>
              <div className="flex flex-wrap gap-1">
                {['0', '1', '2', '3', '4', '5', '6', '7'].map((modeId) => (
                  <button
                    key={modeId}
                    onClick={() => toggleNotifyOnComplete(modeId)}
                    className={clsx(
                      'px-2 py-1 text-xs rounded transition-colors',
                      notifyOnComplete.has(modeId)
                        ? 'bg-accent-blue text-white'
                        : 'bg-bg-primary text-text-secondary hover:bg-bg-hover'
                    )}
                  >
                    Mode {modeId}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function NotificationItem({
  notification,
  onRead,
}: {
  notification: Notification;
  onRead: () => void;
}) {
  const Icon = getNotificationIcon(notification.type);
  const iconColor = getNotificationColor(notification.type);

  return (
    <div
      onClick={onRead}
      className={clsx(
        'flex items-start gap-3 px-4 py-3 cursor-pointer transition-colors',
        notification.read ? 'opacity-60' : 'bg-bg-tertiary/50',
        'hover:bg-bg-hover'
      )}
    >
      <div className={clsx('w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0', `bg-${iconColor}/10`)}>
        <Icon className={clsx('w-4 h-4', `text-${iconColor}`)} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium text-sm">{notification.title}</span>
          {!notification.read && (
            <span className="w-2 h-2 rounded-full bg-accent-blue" />
          )}
        </div>
        {notification.message && (
          <p className="text-sm text-text-secondary mt-0.5 truncate">
            {notification.message}
          </p>
        )}
        <div className="flex items-center gap-3 mt-1">
          <span className="text-2xs text-text-muted">
            {formatDistanceToNow(new Date(notification.timestamp), { addSuffix: true })}
          </span>
          {notification.actionLabel && (
            <button className="text-2xs text-accent-blue hover:underline">
              {notification.actionLabel}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function getNotificationIcon(type: Notification['type']) {
  switch (type) {
    case 'success': return CheckCircle2;
    case 'error': return XCircle;
    case 'warning': return AlertCircle;
    case 'info': return Info;
  }
}

function getNotificationColor(type: Notification['type']) {
  switch (type) {
    case 'success': return 'status-success';
    case 'error': return 'status-error';
    case 'warning': return 'status-warning';
    case 'info': return 'accent-blue';
  }
}
