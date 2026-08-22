import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/api/client";
import { LANDING } from "@/constants/testIds";
import { LogoMark, LogoFull, BrandInline } from "@/components/shared/Brand";
import { ChevronDown, Sparkles, Music2, Wallet, TrendingUp, ShieldCheck, Headphones, Globe2, Users } from "lucide-react";

const ICONS = [Music2, TrendingUp, Wallet, Headphones, ShieldCheck, Users, Sparkles, Globe2];

export default function Landing() {
  const [s, setS] = useState(null);
  const [openFaq, setOpenFaq] = useState(0);
  const [sim, setSim] = useState({ revenue: 100, rate: 17500 });

  useEffect(() => {
    api.get("/cms/landing").then((r) => setS(r.data)).catch(() => setS({}));
  }, []);

  if (!s) {
    return <div className="min-h-screen grid place-items-center text-zinc-500">Memuat…</div>;
  }

  const labelPercent = s.royalty_sim?.label_percent_default ?? 60;
  const labelEur = sim.revenue * (labelPercent / 100);
  const labelIdr = labelEur * sim.rate;

  return (
    <div className="rm-mesh min-h-screen text-white">
      {/* Floating glass navbar */}
      <header className="fixed top-4 left-1/2 -translate-x-1/2 w-[94%] max-w-6xl z-50 rm-glass rounded-full px-4 py-2 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2">
          <LogoMark size={36} />
          <span className="font-display font-extrabold tracking-tight text-white hidden sm:inline">RILIS MUSIK</span>
        </Link>
        <nav className="hidden md:flex items-center gap-7 text-sm font-semibold text-zinc-300">
          <a href="#benefits" className="hover:text-white transition">Fitur</a>
          <a href="#royalty" className="hover:text-white transition">Royalti</a>
          <a href="#pricing" className="hover:text-white transition">Harga</a>
          <a href="#faq" className="hover:text-white transition">FAQ</a>
        </nav>
        <div className="flex items-center gap-2">
          <Link to="/login" data-testid={LANDING.navLogin} className="hidden sm:inline-block text-sm font-semibold text-zinc-200 px-3 py-2 rounded-full hover:bg-white/5 transition">
            Login
          </Link>
          <Link to="/register" data-testid={LANDING.navRegister} className="rm-btn-primary text-sm">
            Daftar
          </Link>
        </div>
      </header>

      {/* HERO */}
      <section className="pt-36 md:pt-44 pb-24 px-6 md:px-12 lg:px-24 relative overflow-hidden">
        <div className="max-w-6xl mx-auto grid md:grid-cols-12 gap-12 items-center">
          <div className="md:col-span-7 rm-fade-up">
            <div className="inline-flex items-center gap-2 rm-glass rounded-full px-3 py-1.5 text-xs font-semibold text-zinc-300 mb-6">
              <Sparkles className="w-3.5 h-3.5 text-[#FF1F8E]" /> Distribusi via Believe ke 150+ DSP
            </div>
            <h1 className="font-display text-5xl md:text-6xl lg:text-7xl font-extrabold leading-[1.02] tracking-tighter">
              Distribusi Musik <span className="rm-gradient-text">Lebih Rapi</span>, Royalti <span className="rm-gradient-text">Lebih Transparan.</span>
            </h1>
            <p className="mt-6 text-lg text-zinc-400 leading-relaxed max-w-xl">
              {s.hero?.subheadline}
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to={s.hero?.cta_primary_url || "/register"} data-testid={LANDING.heroCtaPrimary} className="rm-btn-primary inline-flex items-center gap-2">
                {s.hero?.cta_primary_text || "Daftar Sekarang"}
              </Link>
              <Link to={s.hero?.cta_secondary_url || "/login"} data-testid={LANDING.heroCtaSecondary} className="rm-btn-ghost inline-flex items-center gap-2">
                {s.hero?.cta_secondary_text || "Login Dashboard"}
              </Link>
            </div>
            <div className="mt-10 flex items-center gap-5 text-xs text-zinc-500">
              <div><span className="font-bold text-white">150+</span> platform digital</div>
              <div className="w-px h-4 bg-zinc-700" />
              <div><span className="font-bold text-white">Fleksibel</span> pembagian royalti</div>
              <div className="w-px h-4 bg-zinc-700" />
              <div><span className="font-bold text-white">7 hari</span> minimal release date</div>
            </div>
          </div>

          {/* Hero floating glass artifacts */}
          <div className="md:col-span-5 relative h-[460px]">
            {/* Big brand mark glow */}
            <div className="absolute -top-6 -right-6 w-56 h-56 opacity-90 rm-pulse-glow rm-float">
              <LogoMark size={224} />
            </div>
            <div className="absolute top-44 right-0 w-72 rm-glass-strong rounded-3xl p-5 rm-float">
              <div className="text-xs text-zinc-400 font-semibold uppercase tracking-widest">Saldo Tersedia</div>
              <div className="font-display text-3xl font-extrabold tracking-tight mt-1">Rp 4.275.000</div>
              <div className="text-xs font-bold mt-1 rm-gradient-text">+12% vs bulan lalu</div>
              <div className="mt-4 h-16 flex items-end gap-1.5">
                {[40, 55, 38, 70, 62, 80, 95].map((h, i) => (
                  <div key={i} className="flex-1 rounded-md" style={{ background: `linear-gradient(180deg, #FF1F8E 0%, #A24EFF 100%)`, height: `${h}%` }} />
                ))}
              </div>
            </div>
            <div className="absolute bottom-10 left-0 w-64 rm-glass-strong rounded-3xl p-4 rm-float" style={{ animationDelay: "1.2s" }}>
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl" style={{ background: "linear-gradient(135deg, #FF1F8E, #A24EFF)" }} />
                <div>
                  <div className="text-xs text-zinc-400 font-semibold">Now Streaming</div>
                  <div className="font-semibold text-sm">Senja di Jakarta</div>
                  <div className="text-xs text-zinc-500">Adit Soemardi</div>
                </div>
              </div>
              <div className="mt-3 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                <div className="h-full w-2/3" style={{ background: "linear-gradient(90deg, #FF1F8E, #A24EFF)" }} />
              </div>
              <div className="flex justify-between text-[10px] text-zinc-500 mt-1.5"><span>1:42</span><span>3:08</span></div>
            </div>
            <div className="absolute top-72 left-8 w-44 rm-glass rounded-3xl p-4 rm-float" style={{ animationDelay: "0.6s" }}>
              <div className="text-xs font-semibold text-zinc-400">Status</div>
              <div className="mt-1 inline-flex items-center gap-1.5 text-xs font-bold text-emerald-400">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                LIVE on Spotify
              </div>
              <div className="mt-3 text-[11px] text-zinc-500">ISRC: ID-A1Z-25-12345</div>
            </div>
          </div>
        </div>
      </section>

      {/* BENEFITS */}
      <section id="benefits" className="px-6 md:px-12 lg:px-24 py-20">
        <div className="max-w-6xl mx-auto">
          <div className="max-w-2xl">
            <div className="text-xs uppercase tracking-[0.18em] font-bold rm-gradient-text mb-3">FITUR PLATFORM</div>
            <h2 className="font-display text-4xl md:text-5xl font-extrabold tracking-tighter">Semua yang Anda butuhkan, dalam satu dashboard.</h2>
            <p className="mt-4 text-zinc-400 text-lg">Dari upload rilisan, kelola artist, sampai withdraw. Tanpa WhatsApp.</p>
          </div>
          <div className="mt-12 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 rm-stagger">
            {(s.benefits || []).map((b, i) => {
              const Icon = ICONS[i % ICONS.length];
              return (
                <div key={i} className="rm-glass rounded-3xl p-6 rm-fade-up hover:-translate-y-1 transition-transform duration-300 hover:border-[rgba(255,31,142,0.35)]">
                  <div className="w-12 h-12 rounded-2xl grid place-items-center text-white mb-4" style={{ background: "linear-gradient(135deg, #FF1F8E, #A24EFF)" }}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <div className="font-display font-bold text-lg tracking-tight">{b.title}</div>
                  <div className="text-sm text-zinc-400 mt-2 leading-relaxed">{b.desc}</div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* PLATFORMS */}
      <section id="platforms" className="px-6 md:px-12 lg:px-24 py-16">
        <div className="max-w-6xl mx-auto">
          <div className="text-center max-w-2xl mx-auto mb-10">
            <div className="text-xs uppercase tracking-[0.18em] font-bold rm-gradient-text mb-3">DISTRIBUSI KE 150+ PLATFORM</div>
            <h2 className="font-display text-3xl md:text-4xl font-extrabold tracking-tighter">Lagu Anda tampil di platform terbesar dunia.</h2>
            <p className="mt-3 text-zinc-400">Spotify, Apple Music, YouTube Music, TikTok, dan banyak lagi — semua dalam satu submission.</p>
          </div>
          <div className="rm-glass rounded-[32px] p-6 md:p-10">
            <img
              src="/brand/platforms.png"
              alt="Platform distribusi: Spotify, Apple Music, Deezer, YouTube Music, TikTok, Facebook/Instagram Music, Amazon Music, SoundCloud, Tidal, Shazam, iHeart Radio"
              className="w-full max-w-5xl mx-auto opacity-90 hover:opacity-100 transition-opacity"
              style={{ filter: "drop-shadow(0 0 24px rgba(255,31,142,0.08))" }}
              data-testid="landing-platforms-image"
            />
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="px-6 md:px-12 lg:px-24 py-20">
        <div className="max-w-6xl mx-auto">
          <div className="text-xs uppercase tracking-[0.18em] font-bold rm-gradient-text mb-3">ALUR</div>
          <h2 className="font-display text-4xl md:text-5xl font-extrabold tracking-tighter mb-12">Dari demo ke 150+ platform.</h2>
          <div className="grid md:grid-cols-2 gap-x-12 gap-y-10">
            {(s.how_it_works || []).map((step, i) => (
              <div key={i} className="flex gap-5 rm-fade-up">
                <div className="text-7xl font-display font-extrabold tracking-tighter leading-none -mt-2 rm-gradient-text opacity-25">{String(i + 1).padStart(2, "0")}</div>
                <div className="pt-2">
                  <div className="font-display font-bold text-xl tracking-tight">{step}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* PRICING */}
      <section id="pricing" className="px-6 md:px-12 lg:px-24 py-24">
        <div className="max-w-6xl mx-auto">
          <div className="text-center max-w-2xl mx-auto">
            <div className="text-xs uppercase tracking-[0.18em] font-bold rm-gradient-text mb-3">HARGA</div>
            <h2 className="font-display text-4xl md:text-5xl font-extrabold tracking-tighter">Pilih yang cocok untuk skala Anda.</h2>
            <p className="mt-4 text-zinc-400 text-lg">{s.pricing?.description}</p>
          </div>
          <div className="mt-12 grid md:grid-cols-3 gap-5 max-w-6xl mx-auto">
            {/* Pay Per Release */}
            <div data-testid={LANDING.pricingPay} className="rm-glass rounded-3xl p-7 flex flex-col">
              <div className="text-xs font-bold text-zinc-400 uppercase tracking-widest">Pay Per Release</div>
              <div className="mt-3 flex items-baseline gap-1">
                <span className="font-display text-4xl font-extrabold tracking-tighter">Rp{(s.pricing?.pay_per_release_price ?? 35000).toLocaleString("id-ID")}</span>
                <span className="text-zinc-500 text-xs">/ rilis</span>
              </div>
              <p className="text-sm text-zinc-400 mt-2">Cocok untuk yang baru memulai atau ingin coba.</p>
              <ul className="mt-5 space-y-2 text-sm text-zinc-200 flex-1">
                {(s.pricing?.features_pay || []).map((f, i) => (
                  <li key={i} className="flex items-start gap-2"><span className="rm-gradient-text font-bold mt-0.5">✓</span>{f}</li>
                ))}
                <li className="flex items-start gap-2 text-zinc-400 italic"><span className="text-zinc-600 mt-0.5">+</span>WAMI add-on Rp 100.000/lagu (opsional)</li>
              </ul>
              <Link to="/register" className="rm-btn-ghost mt-7 text-center">Daftar Pay Per Release</Link>
            </div>

            {/* Annual Normal */}
            <div data-testid="landing-pricing-annual-normal" className="rm-glass rounded-3xl p-7 flex flex-col">
              <div className="text-xs font-bold text-zinc-400 uppercase tracking-widest">Annual Normal</div>
              <div className="mt-3 flex items-baseline gap-1">
                <span className="font-display text-4xl font-extrabold tracking-tighter">Rp{(s.pricing?.annual_normal_price ?? 350000).toLocaleString("id-ID")}</span>
                <span className="text-zinc-500 text-xs">/ tahun</span>
              </div>
              <p className="text-sm text-zinc-400 mt-2">Submit unlimited rilisan tanpa biaya per release.</p>
              <ul className="mt-5 space-y-2 text-sm text-zinc-200 flex-1">
                {(s.pricing?.features_annual_normal || ["Submit unlimited release", "Prioritas review", "Tanpa biaya per release"]).map((f, i) => (
                  <li key={i} className="flex items-start gap-2"><span className="rm-gradient-text font-bold mt-0.5">✓</span>{f}</li>
                ))}
                <li className="flex items-start gap-2 text-zinc-400 italic"><span className="text-zinc-600 mt-0.5">+</span>WAMI add-on Rp 100.000/lagu (opsional)</li>
              </ul>
              <Link to="/register" className="rm-btn-ghost mt-7 text-center">Mulai Annual</Link>
            </div>

            {/* Annual VIP */}
            <div data-testid={LANDING.pricingSub} className="rm-glass-strong rounded-3xl p-7 relative flex flex-col" style={{ borderColor: "rgba(255,31,142,0.45)", borderWidth: 1, borderStyle: "solid" }}>
              <div className="absolute -top-3 left-7 text-[10px] font-bold uppercase tracking-widest px-3 py-1 rounded-full text-white" style={{ background: "linear-gradient(135deg, #FF1F8E, #A24EFF)" }}>VIP — Recommended</div>
              <div className="text-xs font-bold text-zinc-400 uppercase tracking-widest mt-1">Annual VIP</div>
              <div className="mt-3 flex items-baseline gap-1">
                <span className="font-display text-4xl font-extrabold tracking-tighter rm-gradient-text">Rp{(s.pricing?.annual_subscription_price ?? 500000).toLocaleString("id-ID")}</span>
                <span className="text-zinc-500 text-xs">/ tahun</span>
              </div>
              <p className="text-sm text-zinc-400 mt-2">Untuk label aktif yang serius — lengkap dengan WAMI gratis & konten promosi.</p>
              <ul className="mt-5 space-y-2 text-sm text-zinc-200 flex-1">
                <li className="flex items-start gap-2"><span className="rm-gradient-text font-bold mt-0.5">✓</span>Submit unlimited release</li>
                <li className="flex items-start gap-2"><span className="rm-gradient-text font-bold mt-0.5">✓</span>Prioritas review</li>
                <li className="flex items-start gap-2"><span className="rm-gradient-text font-bold mt-0.5 text-pink-300">★</span><b>GRATIS</b> daftar LMKN — WAMI semua lagu</li>
                <li className="flex items-start gap-2"><span className="rm-gradient-text font-bold mt-0.5 text-pink-300">★</span><b>GRATIS</b> konten promosi (JPG)</li>
                <li className="flex items-start gap-2"><span className="rm-gradient-text font-bold mt-0.5 text-pink-300">★</span>Status pendaftaran WAMI real-time</li>
              </ul>
              <Link to="/register" className="rm-btn-primary mt-7 text-center">Mulai VIP</Link>
            </div>
          </div>
          <p className="text-center text-xs text-zinc-500 mt-8">Semua paket sudah termasuk distribusi ke 150+ platform digital.</p>
        </div>
      </section>

      {/* ROYALTY SIMULATOR */}
      <section id="royalty" className="px-6 md:px-12 lg:px-24 py-20">
        <div className="max-w-6xl mx-auto rm-glass-strong rounded-[32px] p-8 md:p-12">
          <div className="grid md:grid-cols-2 gap-10 items-center">
            <div>
              <div className="text-xs uppercase tracking-[0.18em] font-bold rm-gradient-text mb-3">SIMULASI ROYALTI</div>
              <h2 className="font-display text-3xl md:text-4xl font-extrabold tracking-tighter">Hitung estimasi pendapatan Anda.</h2>
              <p className="mt-3 text-zinc-400">Masukkan revenue Believe dan kurs EUR/IDR. Hasil bersifat estimasi.</p>
              <div className="mt-6 space-y-4 max-w-sm">
                <div>
                  <label className="rm-label">Revenue (EUR)</label>
                  <input
                    type="number"
                    data-testid={LANDING.simRevenueInput}
                    className="rm-input"
                    value={sim.revenue}
                    onChange={(e) => setSim({ ...sim, revenue: parseFloat(e.target.value || 0) })}
                  />
                </div>
                <div>
                  <label className="rm-label">Kurs EUR → IDR</label>
                  <input
                    type="number"
                    data-testid={LANDING.simRateInput}
                    className="rm-input"
                    value={sim.rate}
                    onChange={(e) => setSim({ ...sim, rate: parseFloat(e.target.value || 0) })}
                  />
                </div>
              </div>
            </div>
            <div className="rm-card p-6 md:p-8">
              <div className="text-xs uppercase tracking-widest text-zinc-400 font-bold">Estimasi Royalti Final</div>
              <div data-testid={LANDING.simResult} className="font-display text-5xl font-extrabold tracking-tighter mt-2 rm-gradient-text">
                Rp {Math.round(labelIdr).toLocaleString("id-ID")}
              </div>
              <div className="text-xs text-zinc-500 mt-1">/ periode estimasi berdasarkan bagian royalti label</div>
              <div className="mt-6 space-y-2 text-sm">
                <Row k="Pendapatan kotor RILIS MUSIK" v={`€${sim.revenue.toLocaleString()}`} />
                <Row k={`Bagian label (${labelPercent}%)`} v={`€${labelEur.toFixed(2)}`} muted />
                <Row k="Kurs EUR → IDR" v={`Rp ${sim.rate.toLocaleString("id-ID")}`} muted />
                <div className="border-t border-white/5 pt-3 mt-2">
                  <Row k="Estimasi royalti final" v={`Rp ${Math.round(labelIdr).toLocaleString("id-ID")}`} bold />
                </div>
              </div>
              <div className="text-[11px] text-zinc-500 mt-4">* Estimasi. Angka final akan ditampilkan di dashboard Anda setiap periode royalti masuk.</div>
            </div>
          </div>
        </div>
      </section>

      {/* TESTIMONIALS */}
      <section className="px-6 md:px-12 lg:px-24 py-20">
        <div className="max-w-6xl mx-auto">
          <div className="text-xs uppercase tracking-[0.18em] font-bold rm-gradient-text mb-3">TESTIMONI</div>
          <h2 className="font-display text-4xl md:text-5xl font-extrabold tracking-tighter mb-10">Dipercaya oleh label & artis Indonesia.</h2>
          <div className="grid md:grid-cols-2 gap-5">
            {(s.testimonials || []).map((t, i) => (
              <div key={i} className="rm-glass rounded-3xl p-7">
                <div className="text-2xl font-display font-extrabold leading-none mb-3 rm-gradient-text">&ldquo;</div>
                <p className="text-lg text-zinc-100 leading-relaxed font-display">{t.quote}</p>
                <div className="mt-5 flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full" style={{ background: "linear-gradient(135deg, #FF1F8E, #A24EFF)" }} />
                  <div>
                    <div className="font-semibold text-sm">{t.name}</div>
                    <div className="text-xs text-zinc-500">{t.role}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section id="faq" className="px-6 md:px-12 lg:px-24 py-20">
        <div className="max-w-3xl mx-auto">
          <div className="text-xs uppercase tracking-[0.18em] font-bold rm-gradient-text mb-3 text-center">FAQ</div>
          <h2 className="font-display text-4xl md:text-5xl font-extrabold tracking-tighter text-center mb-10">Pertanyaan yang sering diajukan.</h2>
          <div className="divide-y divide-white/5">
            {(s.faq || []).map((f, i) => (
              <div key={i} data-testid={`${LANDING.faqItem}-${i}`} className="py-5">
                <button onClick={() => setOpenFaq(openFaq === i ? -1 : i)} className="w-full flex justify-between items-center text-left">
                  <div className="font-display font-bold text-lg tracking-tight pr-4">{f.q}</div>
                  <ChevronDown className={`w-5 h-5 text-zinc-400 transition-transform ${openFaq === i ? "rotate-180" : ""}`} />
                </button>
                {openFaq === i && <div className="mt-3 text-zinc-400 leading-relaxed">{f.a}</div>}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA FINAL */}
      <section className="px-6 md:px-12 lg:px-24 pb-24">
        <div className="max-w-5xl mx-auto rm-glass-strong rounded-[32px] p-10 md:p-14 text-center relative overflow-hidden">
          <div className="absolute inset-0 opacity-30 pointer-events-none" style={{ background: "radial-gradient(60% 50% at 50% 0%, rgba(255,31,142,0.5), transparent 70%)" }} />
          <div className="relative">
            <LogoFull width={140} className="mx-auto mb-6" />
            <h2 className="font-display text-4xl md:text-5xl font-extrabold tracking-tighter">Siap distribusikan musik Anda?</h2>
            <p className="mt-3 text-zinc-400 text-lg">Daftar dalam 2 menit, mulai upload hari ini.</p>
            <div className="mt-7 flex justify-center gap-3 flex-wrap">
              <Link to="/register" className="rm-btn-primary">Daftar Sekarang</Link>
              <Link to="/login" className="rm-btn-ghost">Login Dashboard</Link>
            </div>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="px-6 md:px-12 lg:px-24 pb-14 pt-6 border-t border-white/5" data-testid="landing-footer">
        <div className="max-w-6xl mx-auto grid md:grid-cols-4 gap-8">
          <div>
            <BrandInline size={36} />
            <p className="text-sm text-zinc-500 mt-3 max-w-xs">{s.footer?.description}</p>
          </div>
          <div data-testid="footer-legal-entity">
            <div className="text-xs uppercase tracking-widest font-bold text-zinc-400 mb-3">Badan Hukum</div>
            <div className="text-sm text-zinc-200 font-semibold">{s.legal_entity?.company_name || "PT. Jeeres Group Indonesia"}</div>
            <div className="text-xs text-zinc-500 mt-2 leading-relaxed">
              {s.legal_entity?.address_line1 || "Jl. Sintang Pontianak"}<br/>
              {s.legal_entity?.address_line2 || "RT 12 / RW 5, Kec. Sintang"}<br/>
              {(s.legal_entity?.city || "Sintang")} {(s.legal_entity?.postal_code || "78614")}, {(s.legal_entity?.country || "Indonesia")}
            </div>
            <div className="text-xs text-zinc-500 mt-2">
              NIB: <span className="text-zinc-300 font-mono">{s.legal_entity?.nib || "2202260059749"}</span>
            </div>
          </div>
          <div>
            <div className="text-xs uppercase tracking-widest font-bold text-zinc-400 mb-3">Support</div>
            <div className="text-sm text-zinc-200" data-testid="footer-support-email">{s.footer?.support_email}</div>
            <div className="text-sm text-zinc-500 mt-1" data-testid="footer-whatsapp">WA/HP: {s.legal_entity?.whatsapp || "085864137150"}</div>
          </div>
          <div>
            <div className="text-xs uppercase tracking-widest font-bold text-zinc-400 mb-3">Legal</div>
            <ul className="space-y-2 text-sm text-zinc-200">
              {(s.footer?.legal_links || []).map((l, i) => (
                <li key={i}><a href={l.url} className="hover:rm-gradient-text">{l.text}</a></li>
              ))}
            </ul>
          </div>
        </div>
        <div className="max-w-6xl mx-auto mt-10 pt-6 border-t border-white/5 text-xs text-zinc-500 flex flex-col md:flex-row md:justify-between gap-2">
          <div data-testid="footer-copyright">© {new Date().getFullYear()} RILIS MUSIK — dikelola oleh {s.legal_entity?.company_name || "PT. Jeeres Group Indonesia"}. All rights reserved.</div>
          <Link to="/login" className="hover:text-white">Login Dashboard →</Link>
        </div>
      </footer>
    </div>
  );
}

function Row({ k, v, bold, muted }) {
  return (
    <div className={`flex justify-between ${muted ? "text-zinc-500" : "text-zinc-300"} ${bold ? "font-bold text-white" : ""}`}>
      <span>{k}</span>
      <span>{v}</span>
    </div>
  );
}
