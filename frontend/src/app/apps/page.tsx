import { redirect } from "next/navigation";
import { getSession } from "@/lib/session";
import StandaloneShell from "@/components/dashboard/StandaloneShell";
import AppsListContent from "./AppsListContent";

export const metadata = {
  title: "Apps | APILens",
  description: "Manage your apps",
};

export default async function AppsPage() {
  const session = await getSession();
  if (!session) {
    redirect("/auth/login");
  }

  return (
    <StandaloneShell>
      <AppsListContent />
    </StandaloneShell>
  );
}
