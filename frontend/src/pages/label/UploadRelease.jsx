import React, { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, formatApiError } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { ReleaseFormStepper } from "./release-form/ReleaseFormStepper";
import { ReleaseInfoStep } from "./release-form/ReleaseInfoStep";
import { ArtistCreditsStep } from "./release-form/ArtistCreditsStep";
import { TracksStep } from "./release-form/TracksStep";
import { AssetsReviewStep } from "./release-form/AssetsReviewStep";
import { defaultReleaseForm, mapReleaseToForm, serializeReleaseForm, validateStep } from "./release-form/releaseFormState";

export default function UploadRelease() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { profile, user } = useAuth();
  const [step, setStep] = useState(1);
  const [form, setForm] = useState(defaultReleaseForm());
  const [release, setRelease] = useState(null);
  const [products, setProducts] = useState([]);
  const [selectedAddons, setSelectedAddons] = useState([]);
  const [declaration, setDeclaration] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const isPpr = profile?.payment_type !== "annual_subscription" || profile?.subscription_status !== "active";
  const addonTotal = useMemo(() => products.filter((item) => selectedAddons.includes(item.id)).reduce((sum, item) => sum + Number(item.amount || 0), 0), [products, selectedAddons]);

  useEffect(() => {
    api.get("/payments/products").then(({ data }) => setProducts(data || [])).catch(() => {});
    if (!id) return;
    api.get(`/releases/${id}`).then(({ data }) => {
      setRelease(data); setForm(mapReleaseToForm(data));
      setSelectedAddons(data.selected_addon_product_ids || []);
    }).catch((requestError) => setError(formatApiError(requestError.response?.data?.detail) || "Gagal memuat draft"));
  }, [id]);

  const updateForm = (patch) => setForm((current) => ({ ...current, ...patch }));
  const goNext = () => {
    const message = validateStep(step, form);
    if (message) { setError(message); return; }
    setError(""); setStep((value) => Math.min(value + 1, 4));
  };
  const reloadRelease = async (releaseId) => {
    const { data } = await api.get(`/releases/${releaseId}`);
    setRelease(data); setForm(mapReleaseToForm(data)); return data;
  };
  const saveDraft = async () => {
    const message = validateStep(3, form);
    if (message) { setError(message); return; }
    setSaving(true); setError("");
    try {
      const payload = serializeReleaseForm(form);
      const { data } = release?.id
        ? await api.patch(`/releases/${release.id}`, payload)
        : await api.post("/releases/draft", payload);
      await reloadRelease(data.id); setStep(4);
    } catch (requestError) {
      setError(formatApiError(requestError.response?.data?.detail) || "Gagal menyimpan draft");
    } finally { setSaving(false); }
  };
  const submit = async () => {
    if (!declaration) { setError("Deklarasi hak cipta wajib disetujui"); return; }
    setSaving(true); setError("");
    try {
      const { data } = await api.post(`/releases/${release.id}/submit`, {
        contract_declaration_checked: true,
        addon_product_ids: isPpr ? selectedAddons : [],
      });
      navigate(`/label/releases/${data.id}`);
    } catch (requestError) {
      setError(formatApiError(requestError.response?.data?.detail) || "Submit gagal");
    } finally { setSaving(false); }
  };

  return <div className="max-w-6xl space-y-7 pb-20">
    <header><div className="text-xs font-bold uppercase text-zinc-500">Distribusi Musik</div><h1 className="mt-1 font-display text-4xl font-extrabold tracking-normal">{id ? "Edit Rilisan" : "Submit Rilisan Baru"}</h1><p className="mt-2 max-w-3xl text-sm text-zinc-400">Lengkapi metadata, kredit, track, cover 3000×3000, dan WAV 44,1/48 kHz sebelum dikirim ke admin.</p></header>
    <ReleaseFormStepper step={step} onStep={(value) => value < step && setStep(value)} />
    {error && <div role="alert" className="rounded-md border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-200" data-testid="upload-release-error-alert">{error}</div>}
    {release?.status === "need_revision" && release.admin_note && <div className="border-l-2 border-amber-400 bg-amber-500/10 px-4 py-3 text-sm text-amber-100" data-testid="upload-release-revision-note"><strong>Catatan revisi admin:</strong> {release.admin_note}</div>}
    {step === 1 && <ReleaseInfoStep form={form} updateForm={updateForm} labelName={profile?.label_name} responsibleName={user?.name || profile?.pic_name} onNext={goNext} />}
    {step === 2 && <ArtistCreditsStep form={form} updateForm={updateForm} onBack={() => setStep(1)} onNext={goNext} />}
    {step === 3 && <TracksStep form={form} updateForm={updateForm} saving={saving} onBack={() => setStep(2)} onSave={saveDraft} />}
    {step === 4 && release && <AssetsReviewStep release={release} products={products} selectedAddons={selectedAddons} setSelectedAddons={setSelectedAddons} isPpr={isPpr} addonTotal={addonTotal} declaration={declaration} setDeclaration={setDeclaration} saving={saving} setError={setError} reloadRelease={reloadRelease} onBack={() => setStep(3)} onSubmit={submit} />}
  </div>;
}