import React, { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Search } from "lucide-react";
import { useAdminNavigation } from "@/contexts/AdminNavigationContext";
import { staffHome } from "./workspaceNavigation";

export default function V7MenuSearch() {
  const { items, labelFor } = useAdminNavigation();
  const { pathname } = useLocation();
  const [query, setQuery] = useState("");
  const field = useRef(null);
  useEffect(() => { setQuery(""); }, [pathname]);
  useEffect(() => {
    const keydown = event => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") { event.preventDefault(); field.current?.focus(); }
      if (event.key === "Escape") setQuery("");
    };
    window.addEventListener("keydown", keydown);
    return () => window.removeEventListener("keydown", keydown);
  }, []);
  const matches = [staffHome, ...items].filter(item => item.visible !== false && labelFor(item).toLowerCase().includes(query.trim().toLowerCase())).slice(0, 8);
  return <div className="v7-menu-search"><Search size={15} /><input ref={field} aria-label="Cari menu" placeholder="Cari menu…" value={query} onChange={event => setQuery(event.target.value)} /><kbd>⌘ / Ctrl K</kbd>{query.trim() && <div className="v7-search-results" aria-label="Hasil pencarian menu">{matches.length ? matches.map(item => <Link to={item.route} key={item.key} onClick={() => setQuery("")}>{labelFor(item)}</Link>) : <p>Tidak ada menu yang cocok.</p>}</div>}</div>;
}
