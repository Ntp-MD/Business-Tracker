import Image from "next/image";

export function BrandLogo() {
  return (
    <Image
      className="logo-img"
      src="/assets/trendrail-logo.png"
      alt="TrendRail"
      width={2170}
      height={565}
      priority
    />
  );
}
