import { redirect } from "next/navigation";
import { getSession } from "@/lib/session";
import StandaloneShell from "@/components/dashboard/StandaloneShell";
import { CreateAppForm } from "@/components/apps";

export const metadata = {
  title: "Create App | APILens",
  description: "Create a new app",
};

export default async function NewAppPage() {
  const session = await getSession();
  if (!session) {
    redirect("/auth/login");
  }

  return (
    <StandaloneShell>
      <div className="create-app-page">
        <h1 className="create-app-page-title">Create a new app</h1>
        <p className="create-app-page-description">
          Apps group your API keys and monitoring configuration.
        </p>
        <CreateAppForm />
      </div>
    </StandaloneShell>
  );
}
