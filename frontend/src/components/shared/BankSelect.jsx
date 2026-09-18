import React, { useState } from "react";
import { Check, ChevronsUpDown, Landmark } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { INDONESIA_BANKS, findBank } from "@/data/indonesiaBanks";
import { cn } from "@/lib/utils";

// Searchable single-select bank dropdown. `value` is a bank slug; falls back to
// resolving a legacy free-text name so edit mode shows the previously saved bank.
export function BankSelect({ value, onChange, placeholder = "Pilih bank", testid = "bank-select" }) {
  const [open, setOpen] = useState(false);
  const current = findBank(value);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          role="combobox"
          aria-expanded={open}
          className="rm-input flex w-full items-center justify-between gap-2 text-left"
          data-testid={testid}
        >
          <span className={cn("flex items-center gap-2 truncate", !current && "text-zinc-500")}>
            <Landmark className="h-4 w-4 shrink-0 text-zinc-400" />
            {current ? current.label : placeholder}
          </span>
          <ChevronsUpDown className="h-4 w-4 shrink-0 opacity-50" />
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-[--radix-popover-trigger-width] min-w-[260px] p-0" align="start">
        <Command>
          <CommandInput placeholder="Cari atau pilih bank..." data-testid={`${testid}-search`} />
          <CommandList>
            <CommandEmpty>Bank tidak ditemukan.</CommandEmpty>
            <CommandGroup>
              {INDONESIA_BANKS.map((bank) => (
                <CommandItem
                  key={bank.value}
                  value={bank.label}
                  keywords={bank.keywords}
                  onSelect={() => { onChange(bank.value, bank.label); setOpen(false); }}
                  data-testid={`${testid}-option-${bank.value}`}
                >
                  <Check className={cn("mr-2 h-4 w-4", current?.value === bank.value ? "opacity-100" : "opacity-0")} />
                  {bank.label}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
