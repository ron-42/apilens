import { redirect } from "next/navigation";
import { getSession } from "@/lib/session";
import { DashboardLayout } from "@/components/dashboard";

export default async function AppLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ slug: string }>;
}) {
  const session = await getSession();
  if (!session) {
    redirect("/auth/login");
  }

  const { slug } = await params;

  return <DashboardLayout appSlug={slug}>{children}</DashboardLayout>;
}
