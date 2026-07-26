import { ProductDetailDashboard } from "@/components/product-detail-dashboard";

export default async function ProductDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ProductDetailDashboard productId={id} />;
}
