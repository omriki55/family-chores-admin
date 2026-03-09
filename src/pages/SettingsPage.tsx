import { useState, useEffect } from "react";
import { useAuthContext } from "@/context/AuthContext";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getAdminConfig, setAdminConfig,
  getFamilyRegistry, registerFamily, removeFamily,
  discoverFromLegacy,
} from "@/lib/firestore";
import { collection, getDocs } from "firebase/firestore";
import { db } from "@/lib/firebase";
import { toast } from "sonner";
import { Plus, Trash2, LogOut, RefreshCw, Server, Shield, Users, Mail, Database } from "lucide-react";
import { seedSampleData } from "@/lib/seed-data";

export default function SettingsPage() {
  const { user, signOut } = useAuthContext();

  // Admin emails state
  const [adminEmails, setAdminEmails] = useState<string[]>([]);
  const [newAdminEmail, setNewAdminEmail] = useState("");
  const [loadingEmails, setLoadingEmails] = useState(true);

  // Family registry state
  const [registeredFamilies, setRegisteredFamilies] = useState<Array<{ familyId: string; [key: string]: any }>>([]);
  const [newFamilyId, setNewFamilyId] = useState("");
  const [loadingFamilies, setLoadingFamilies] = useState(true);
  const [discovering, setDiscovering] = useState(false);
  const [seeding, setSeeding] = useState(false);

  // Load admin config
  useEffect(() => {
    (async () => {
      setLoadingEmails(true);
      try {
        const config = await getAdminConfig();
        setAdminEmails(config?.adminEmails || []);
      } catch (e) {
        console.error("Failed to load admin config:", e);
      }
      setLoadingEmails(false);
    })();
  }, []);

  // Load family registry
  useEffect(() => {
    loadFamilyRegistry();
  }, []);

  const loadFamilyRegistry = async () => {
    setLoadingFamilies(true);
    try {
      const families = await getFamilyRegistry();
      setRegisteredFamilies(families);
    } catch (e) {
      console.error("Failed to load family registry:", e);
    }
    setLoadingFamilies(false);
  };

  // Admin email handlers
  const handleAddEmail = async () => {
    const email = newAdminEmail.trim().toLowerCase();
    if (!email || !email.includes("@")) {
      toast.error("Please enter a valid email address");
      return;
    }
    if (adminEmails.includes(email)) {
      toast.error("Email already in admin list");
      return;
    }
    try {
      const updated = [...adminEmails, email];
      await setAdminConfig({ adminEmails: updated });
      setAdminEmails(updated);
      setNewAdminEmail("");
      toast.success("Admin email added");
    } catch (e) {
      toast.error("Failed to add admin email");
    }
  };

  const handleRemoveEmail = async (email: string) => {
    if (adminEmails.length <= 1) {
      toast.error("Cannot remove the last admin email");
      return;
    }
    try {
      const updated = adminEmails.filter((e) => e !== email);
      await setAdminConfig({ adminEmails: updated });
      setAdminEmails(updated);
      toast.success("Admin email removed");
    } catch (e) {
      toast.error("Failed to remove admin email");
    }
  };

  // Family registry handlers
  const handleAddFamily = async () => {
    const fid = newFamilyId.trim();
    if (!fid) return;
    try {
      await registerFamily(fid, { familyName: fid, addedManually: true });
      setNewFamilyId("");
      toast.success("Family registered");
      loadFamilyRegistry();
    } catch (e) {
      toast.error("Failed to register family");
    }
  };

  const handleRemoveFamily = async (familyId: string) => {
    try {
      await removeFamily(familyId);
      toast.success("Family removed from registry");
      loadFamilyRegistry();
    } catch (e) {
      toast.error("Failed to remove family");
    }
  };

  const handleAutoDiscover = async () => {
    setDiscovering(true);
    try {
      const existingIds = new Set(registeredFamilies.map((f) => f.familyId));
      let added = 0;

      // Strategy 1: Scan families collection for parent docs
      try {
        const colRef = collection(db, "families");
        const snapshot = await getDocs(colRef);
        for (const d of snapshot.docs) {
          if (!existingIds.has(d.id)) {
            await registerFamily(d.id, { familyName: d.id, autoDiscovered: true });
            existingIds.add(d.id);
            added++;
          }
        }
      } catch {}

      // Strategy 2: Check legacy "family-chores" collection for family-config
      try {
        const legacy = await discoverFromLegacy();
        if (legacy.familyId && !existingIds.has(legacy.familyId)) {
          await registerFamily(legacy.familyId, {
            familyName: legacy.familyName || legacy.familyId,
            autoDiscovered: true,
            source: "legacy",
          });
          existingIds.add(legacy.familyId);
          added++;
        }
      } catch {}

      if (added > 0) {
        toast.success(`Discovered and registered ${added} new families`);
        loadFamilyRegistry();
      } else {
        toast.info("No new families found — try adding a Family ID manually");
      }
    } catch (e) {
      toast.error("Auto-discovery failed");
    }
    setDiscovering(false);
  };

  const handleSeedData = async () => {
    setSeeding(true);
    try {
      const familyId = await seedSampleData();
      toast.success(`Sample data created for family ${familyId}`);
      loadFamilyRegistry();
    } catch (e) {
      console.error("Seed failed:", e);
      toast.error("Failed to seed sample data");
    }
    setSeeding(false);
  };

  const projectId = import.meta.env.VITE_FIREBASE_PROJECT_ID || "Not configured";

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Settings</h1>

      {/* Admin Profile */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Shield className="h-4 w-4" />
            Admin Profile
          </CardTitle>
        </CardHeader>
        <CardContent>
          {user ? (
            <div className="flex items-center gap-4">
              <Avatar className="h-14 w-14">
                <AvatarImage src={user.photoURL || undefined} alt={user.displayName || "Admin"} />
                <AvatarFallback>{(user.displayName || "A").charAt(0).toUpperCase()}</AvatarFallback>
              </Avatar>
              <div className="flex-1">
                <p className="font-medium text-lg">{user.displayName || "Admin"}</p>
                <p className="text-sm text-muted-foreground">{user.email}</p>
              </div>
              <Badge variant="default">Admin</Badge>
            </div>
          ) : (
            <p className="text-muted-foreground">Not signed in</p>
          )}
        </CardContent>
      </Card>

      {/* Admin Emails */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Mail className="h-4 w-4" />
            Admin Emails
          </CardTitle>
          <CardDescription>Users with these emails can access the admin panel</CardDescription>
        </CardHeader>
        <CardContent>
          {loadingEmails ? (
            <div className="space-y-3">
              {[1, 2].map((i) => <Skeleton key={i} className="h-10 w-full" />)}
            </div>
          ) : (
            <div className="space-y-3">
              {adminEmails.map((email) => (
                <div key={email} className="flex items-center justify-between p-2 rounded-md bg-muted/50">
                  <span className="text-sm">{email}</span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-destructive hover:text-destructive"
                    onClick={() => handleRemoveEmail(email)}
                    disabled={adminEmails.length <= 1}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}

              <div className="flex gap-2 mt-3">
                <Input
                  placeholder="new-admin@example.com"
                  value={newAdminEmail}
                  onChange={(e) => setNewAdminEmail(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleAddEmail()}
                />
                <Button onClick={handleAddEmail} size="sm">
                  <Plus className="h-4 w-4 mr-1" />
                  Add
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Family Registry */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                <Users className="h-4 w-4" />
                Family Registry
              </CardTitle>
              <CardDescription className="mt-1">Families being monitored by the admin panel</CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={handleAutoDiscover} disabled={discovering}>
              <RefreshCw className={`h-4 w-4 mr-1 ${discovering ? "animate-spin" : ""}`} />
              Auto-Discover
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {loadingFamilies ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => <Skeleton key={i} className="h-10 w-full" />)}
            </div>
          ) : (
            <div className="space-y-3">
              {registeredFamilies.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4 text-center">
                  No families registered. Use Auto-Discover or add manually.
                </p>
              ) : registeredFamilies.map((f) => (
                <div key={f.familyId} className="flex items-center justify-between p-2 rounded-md bg-muted/50">
                  <div>
                    <span className="text-sm font-medium">{f.familyName || f.familyId}</span>
                    <code className="ml-2 text-xs bg-muted px-1.5 py-0.5 rounded">{f.familyId}</code>
                    {f.autoDiscovered && (
                      <Badge variant="secondary" className="ml-2 text-xs">auto</Badge>
                    )}
                    {f.addedManually && (
                      <Badge variant="outline" className="ml-2 text-xs">manual</Badge>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-destructive hover:text-destructive"
                    onClick={() => handleRemoveFamily(f.familyId)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}

              <div className="flex gap-2 mt-3">
                <Input
                  placeholder="Family ID (e.g., ABC123)"
                  value={newFamilyId}
                  onChange={(e) => setNewFamilyId(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleAddFamily()}
                />
                <Button onClick={handleAddFamily} size="sm">
                  <Plus className="h-4 w-4 mr-1" />
                  Add
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Seed Sample Data */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Database className="h-4 w-4" />
            Sample Data
          </CardTitle>
          <CardDescription>
            Create a demo family with realistic data for testing the admin panel
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={handleSeedData} disabled={seeding} variant="outline" className="w-full">
            {seeding ? (
              <>
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                Creating sample data...
              </>
            ) : (
              <>
                <Database className="h-4 w-4 mr-2" />
                Seed Sample Family Data
              </>
            )}
          </Button>
          <p className="text-xs text-muted-foreground mt-2 text-center">
            Creates "DEMO01" family with 3 children, tasks, completions, XP, messages, and more
          </p>
        </CardContent>
      </Card>

      {/* Firebase Project */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Server className="h-4 w-4" />
            Firebase Project
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground">Project ID:</span>
            <code className="text-sm bg-muted px-2 py-1 rounded">{projectId}</code>
          </div>
        </CardContent>
      </Card>

      {/* Sign Out */}
      <Card>
        <CardContent className="pt-6">
          <Button variant="destructive" onClick={signOut} className="w-full">
            <LogOut className="h-4 w-4 mr-2" />
            Sign Out
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
