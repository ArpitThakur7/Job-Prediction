import JobDetailClient from "./JobDetailClient";

export function generateStaticParams() {
  return [{ id: "sample" }];
}

export default async function JobDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const resolvedParams = await params;
  return <JobDetailClient id={resolvedParams.id} />;
}
