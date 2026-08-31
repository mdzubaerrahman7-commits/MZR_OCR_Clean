"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const TABS = [
  { href: "", label: "Overview" },
  { href: "/documents", label: "Documents & Mapping" },
  { href: "/entitlement", label: "Entitlement Master" },
  { href: "/imports", label: "Imports" },
  { href: "/exceptions", label: "Exceptions" },
  { href: "/findings", label: "Findings" },
  { href: "/reports", label: "Reports" },
];

export function AuditNav({ auditId }: { auditId: string }) {
  const pathname = usePathname();
  const base = `/audits/${auditId}`;

  return (
    <nav className="mb-4 flex flex-wrap gap-1 border-b border-border">
      {TABS.map((tab) => {
        const href = `${base}${tab.href}`;
        const active = pathname === href;
        return (
          <Link
            key={tab.href}
            href={href}
            className={cn(
              "rounded-t-md px-3 py-2 text-sm",
              active ? "border-b-2 border-primary font-medium text-foreground" : "text-muted-foreground hover:text-foreground"
            )}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
