import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import App from "./App";

vi.mock("./components/ChatWidget", () => ({ default: () => null }));
vi.mock("./services/api", () => ({ getMenu: vi.fn(() => Promise.resolve([])) }));

describe("App navigation", () => {
  it("keeps one reservation link in the navbar with the booking arrow", () => {
    render(<App />);

    const navigation = screen.getByRole("navigation", { name: "Navegación principal" });
    expect(navigation.querySelectorAll('a[href="#reservas"]')).toHaveLength(0);
    expect(screen.getAllByRole("link", { name: /Reserva tu mesa/ })).toHaveLength(1);
    expect(screen.getByRole("link", { name: /Reserva tu mesa/ })).toHaveAttribute("href", "#reservas");
  });
});

describe("App footer", () => {
  it("shows the signature and contact icon links", () => {
    render(<App />);

    expect(screen.getByText("Hecho con calma por Patricio Rodríguez.")).toBeInTheDocument();
    expect(screen.queryByText(/Volver arriba/)).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /email/i })).toHaveAttribute("href", "mailto:patriciorodriguezramirez@gmail.com");
    expect(screen.getByRole("link", { name: /LinkedIn/ })).toHaveAttribute("href", "https://www.linkedin.com/in/patriciorr");
    expect(screen.getByRole("link", { name: /GitHub/ })).toHaveAttribute("href", "https://github.com/patriciorr");
  });
});
