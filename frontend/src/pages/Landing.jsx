import React, { useEffect, useState } from "react";
import { api } from "@/api/client";
import {
  BenefitsSection, HeroSection, LandingFooter, LandingHeader,
  PlatformsAndFlow, PricingSection, RoyaltySection, SocialProofAndFaq,
} from "@/components/landing/LandingSections";

export default function Landing() {
  const [settings, setSettings] = useState(null);
  const [openFaq, setOpenFaq] = useState(0);
  const [simulation, setSimulation] = useState({ revenue: 100, rate: 17500 });

  useEffect(() => {
    let active = true;
    api.get("/cms/landing")
      .then((response) => active && setSettings(response.data))
      .catch(() => active && setSettings({}));
    return () => { active = false; };
  }, []);

  if (!settings) return <div className="min-h-screen grid place-items-center text-zinc-500">Memuat…</div>;
  return <div className="rm-mesh min-h-screen text-white">
    <LandingHeader />
    <HeroSection settings={settings} />
    <BenefitsSection benefits={settings.benefits} />
    <PlatformsAndFlow steps={settings.how_it_works} />
    <PricingSection pricing={settings.pricing} />
    <RoyaltySection settings={settings} simulation={simulation} setSimulation={setSimulation} />
    <SocialProofAndFaq settings={settings} openFaq={openFaq} setOpenFaq={setOpenFaq} />
    <LandingFooter settings={settings} />
  </div>;
}