import React from "react";
import { Disc3 } from "lucide-react";

export default function LogoMark({ className = "h-8 w-8" }) {
  return <span className={`${className} grid shrink-0 place-items-center rounded-md bg-white text-black`} aria-hidden="true"><Disc3 className="h-[62%] w-[62%]" /></span>;
}