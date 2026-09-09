import React, { forwardRef, useSyncExternalStore } from "react";
import { getLocale, subscribeLocale, translateUi } from "./languageStore";

export const useUiLocale = () => useSyncExternalStore(subscribeLocale, getLocale, () => "id");
export const SystemText = ({ source, values = [] }) => {
  const locale = useUiLocale();
  const text = translateUi(source, locale);
  if (typeof text !== "string" || !values.length) return text;
  return text.split(/(\{\d+\})/).map((part, index) => /^\{\d+\}$/.test(part)
    ? React.createElement(React.Fragment, { key: index }, values[Number(part.slice(1, -1))]) : part);
};

const interpolate = (text, values) => text.replace(/\{(\d+)\}/g, (_, index) => String(values[Number(index)] ?? ""));
export const SystemElement = forwardRef(function SystemElement({ as: Component, ui = {}, uiText, children, ...props }, ref) {
  const locale = useUiLocale();
  const translated = Object.fromEntries(Object.entries(ui).map(([key, value]) => [key,
    typeof value === "string" ? translateUi(value, locale) : interpolate(translateUi(value.source, locale), value.values || []),
  ]));
  const content = uiText === undefined ? children : typeof uiText === "string" ? translateUi(uiText, locale) : uiText && typeof uiText === "object" && "source" in uiText ? interpolate(translateUi(uiText.source, locale), uiText.values || []) : uiText;
  const originalText = typeof uiText === "string" ? uiText : uiText && typeof uiText === "object" && "source" in uiText ? interpolate(uiText.source, uiText.values || []) : undefined;
  const optionValue = Component === "option" && props.value === undefined && originalText !== undefined ? { value: originalText } : {};
  return React.createElement(Component, { ...props, ...translated, ...optionValue, ref }, content);
});