import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SocialLinks } from "../src/components/SocialLinks";

describe("SocialLinks", () => {
  it("renders compact icon-only links for Hawatch social profiles", () => {
    render(<SocialLinks />);

    const socialNav = screen.getByRole("navigation", { name: "شبکه‌های اجتماعی هواچ" });
    const links = Array.from(socialNav.querySelectorAll("a"));

    expect(links).toHaveLength(2);
    expect(links[0]).toHaveAttribute("href", "https://www.instagram.com/hawatchir/");
    expect(links[1]).toHaveAttribute("href", "https://t.me/hawatchir");
    expect(links.every((link) => link.getAttribute("target") === "_blank")).toBe(true);
    expect(links.every((link) => link.querySelector("svg"))).toBe(true);
    expect(screen.getByLabelText("اینستاگرام هواچ")).toBeInTheDocument();
    expect(screen.getByLabelText("تلگرام هواچ")).toBeInTheDocument();
  });
});
