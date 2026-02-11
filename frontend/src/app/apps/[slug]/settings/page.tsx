import { redirect } from "next/navigation";

export default async function AppSettingsRedirect({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  redirect(`/apps/${id}/settings/general`);
}
