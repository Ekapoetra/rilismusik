import { api } from "@/api/client";

// Download a finalized-period payslip PDF. Pass staffUserId to fetch another
// staff's slip (admin, requires compensation.view_team); omit for own slip.
export async function downloadPayslip(periodId, staffUserId) {
  const url = `/compensation/payslip/${periodId}${staffUserId ? `?staff_user_id=${encodeURIComponent(staffUserId)}` : ""}`;
  try {
    const res = await api.get(url, { responseType: "blob" });
    const disp = res.headers?.["content-disposition"] || "";
    const match = /filename="?([^"]+)"?/.exec(disp);
    const filename = match ? match[1] : "slip-gaji.pdf";
    const blobUrl = window.URL.createObjectURL(res.data);
    const a = document.createElement("a");
    a.href = blobUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(blobUrl);
  } catch (err) {
    // Error bodies arrive as a Blob under responseType:"blob"; unwrap the detail.
    if (err.response?.data instanceof Blob) {
      try {
        const text = await err.response.data.text();
        err.response.data = JSON.parse(text);
      } catch (_e) {
        /* leave as-is */
      }
    }
    throw err;
  }
}
