import { Upload, Sliders, List, Settings } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ThemeToggle } from "@/components/ThemeToggle";
import { BeginnerTab } from "@/components/BeginnerTab";
import { AdvancedTab } from "@/components/AdvancedTab";
import { JobsPanel } from "@/components/JobsPanel";
import { SettingsTab } from "@/components/SettingsTab";
import logoHorizontal from "@assets/vl_full_logo_horizontal.png";

export default function Home() {
  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center justify-between gap-4 px-4 mx-auto">
          <div className="flex items-center">
            <img 
              src={logoHorizontal} 
              alt="VoxLibris" 
              className="h-10 w-auto"
            />
          </div>
          <ThemeToggle />
        </div>
      </header>

      <main className="container mx-auto px-4 py-6">
        <Tabs defaultValue="beginner" className="w-full">
          <TabsList className="grid w-full grid-cols-4 max-w-lg mx-auto mb-6">
            <TabsTrigger value="beginner" className="gap-2" data-testid="tab-beginner">
              <Upload className="h-4 w-4" />
              <span className="hidden sm:inline">Beginner</span>
            </TabsTrigger>
            <TabsTrigger value="advanced" className="gap-2" data-testid="tab-advanced">
              <Sliders className="h-4 w-4" />
              <span className="hidden sm:inline">Advanced</span>
            </TabsTrigger>
            <TabsTrigger value="jobs" className="gap-2" data-testid="tab-jobs">
              <List className="h-4 w-4" />
              <span className="hidden sm:inline">Jobs</span>
            </TabsTrigger>
            <TabsTrigger value="settings" className="gap-2" data-testid="tab-settings">
              <Settings className="h-4 w-4" />
              <span className="hidden sm:inline">Settings</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="beginner">
            <BeginnerTab />
          </TabsContent>

          <TabsContent value="advanced">
            <AdvancedTab />
          </TabsContent>

          <TabsContent value="jobs">
            <div className="max-w-4xl mx-auto">
              <JobsPanel />
            </div>
          </TabsContent>

          <TabsContent value="settings">
            <div className="max-w-4xl mx-auto">
              <SettingsTab />
            </div>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
