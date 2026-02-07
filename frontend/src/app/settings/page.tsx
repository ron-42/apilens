import { redirect } from "next/navigation";
import { auth0 } from "@/lib/auth0";

export default async function Settings() {
  const session = await auth0.getSession();

  if (!session) {
    redirect("/auth/login");
  }

  // Redirect to default tab
  redirect("/settings/general");
}
