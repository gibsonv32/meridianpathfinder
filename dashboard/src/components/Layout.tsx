import { Sidebar } from './Sidebar';
import { ActivityFeed } from './ActivityFeed';
import { CommandInput } from './CommandInput';
import { ArtifactViewer } from './ArtifactViewer';
import { SearchModal } from './SearchModal';
import { useDashboardStore } from '../store';

export function Layout() {
  const selectedArtifact = useDashboardStore((s) => s.selectedArtifact);
  const searchOpen = useDashboardStore((s) => s.searchOpen);

  return (
    <div className="flex h-screen overflow-hidden">
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

      {/* Right Panel - Artifact Viewer (conditional) */}
      {selectedArtifact && <ArtifactViewer />}

      {/* Search Modal */}
      {searchOpen && <SearchModal />}
    </div>
  );
}
