'use client';

import dynamic from 'next/dynamic';

const NotificationBell = dynamic(
  () => import('./notification-bell').then((mod) => ({ default: mod.NotificationBell })),
  { ssr: false }
);

export function NotificationBellWrapper() {
  return <NotificationBell />;
}
