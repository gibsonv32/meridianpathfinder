import { useEffect } from 'react';
import { Sidebar } from './Sidebar';
import { ActivityFeed } from './ActivityFeed';
import { CommandInput } from './CommandInput';
import { ContextDrawer } from './ContextDrawer';
import { SearchModal } from './SearchModal';
import { useDashboardStore } from '../store';

export function Layout() {
  const searchOpen = useDashboardStore((s) => s.searchOpen);
  const setSearchOpen = useDashboardStore((s) => s.setSearchOpen);

  // Cmd+K to open Command Palette
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setSearchOpen(true);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [setSearchOpen]);

  return (
    <div className="flex h-screen overflow-hidden bg-bg-primary">
      {/* Left Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Activity Feed */}
        <div className="flex-1 overflow-hidden">
          <ActivityFeed />
        </div>

        {/* Command Input */}
        <CommandInput />
      </div>

      {/* Right Panel - Context Drawer (always visible, collapsed by default) */}
      <ContextDrawer />

      {/* Command Palette / Search Modal (Cmd+K) */}
      {searchOpen && <SearchModal />}
    </div>
  );
}
