import { redirect } from "next/navigation";

export default async function AppSettingsRedirect({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  redirect(`/apps/${slug}/settings/general`);
}

