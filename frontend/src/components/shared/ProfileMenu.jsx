import React from "react";
import { LogOut, User } from "lucide-react";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator } from "@/components/ui/dropdown-menu";

const initials = (name) => (name || "?").trim().split(/\s+/).slice(0, 2).map((p) => p[0]).join("").toUpperCase() || "?";

export const ProfileMenu = ({ user, logout, instance = "admin" }) => {
  const { t } = useAppPreferences();
  const name = user?.name || user?.pic_name || user?.email || "Admin";
  const roleName = user?.role_name || user?.role;
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button type="button" className="ui-icon-button overflow-hidden p-0" title={t("Profil")} aria-label={t("Profil")} data-testid={`profile-menu-${instance}`}>
          <span className="grid h-8 w-8 place-items-center rounded-full bg-gradient-to-br from-[#FF1F8E] to-[#A24EFF] text-[11px] font-extrabold text-white" translate="no">{initials(name)}</span>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="ui-menu w-56" align="end" data-testid={`profile-dropdown-${instance}`}>
        <div className="flex items-center gap-3 px-2 py-2.5" translate="no">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-gradient-to-br from-[#FF1F8E] to-[#A24EFF] text-xs font-extrabold text-white">{initials(name)}</span>
          <div className="min-w-0">
            <div className="truncate text-sm font-bold" data-testid={`profile-name-${instance}`}>{name}</div>
            <div className="truncate text-[11px] text-[var(--ui-muted)]" data-testid={`profile-role-${instance}`}>{roleName}</div>
          </div>
        </div>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={logout} className="text-red-400 focus:text-red-400" data-testid={`profile-logout-${instance}`}>
          <LogOut className="mr-2 h-4 w-4" /> {t("Keluar")}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};
