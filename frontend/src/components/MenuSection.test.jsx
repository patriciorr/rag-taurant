import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import MenuSection from "./MenuSection";

const menu = [
  {
    id: "gazpacho",
    name: "Gazpacho andaluz",
    description: "Tomate y aceite de oliva.",
    price: 8.5,
    category: "entrante",
    image_url: "/assets/menu/gazpacho.jpg",
    is_vegan: true,
    is_vegetarian: true,
    available: true,
    allergens: [],
  },
  {
    id: "pisto",
    name: "Pisto de la huerta",
    description: "Verduras de temporada.",
    price: 15,
    category: "principal",
    image_url: "/assets/menu/pisto.jpg",
    is_vegan: false,
    is_vegetarian: true,
    available: true,
    allergens: ["huevo"],
  },
];

describe("MenuSection", () => {
  it("shows category tabs and dietary badges without adding dietary filters", () => {
    render(<MenuSection menu={menu} loading={false} error="" />);

    expect(screen.getByRole("tab", { name: "Entrantes" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("heading", { name: "Gazpacho andaluz" })).toBeInTheDocument();
    expect(screen.getByText("Vegano")).toBeInTheDocument();
    expect(document.querySelector(".dish-photo-wrap .dish-diet-badge")).toHaveTextContent("Vegano");
    expect(document.querySelector(".dish-body .dish-diet-badge")).not.toBeInTheDocument();
    expect(screen.queryByRole("search")).not.toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Principales" }));

    expect(screen.getByRole("heading", { name: "Pisto de la huerta" })).toBeInTheDocument();
    expect(screen.getByText("Vegetariano")).toBeInTheDocument();
    expect(document.querySelector(".dish-photo-wrap .dish-diet-badge")).toHaveTextContent("Vegetariano");
    expect(document.querySelector(".dish-body .dish-diet-badge")).not.toBeInTheDocument();
    const allergenIcon = screen.getByRole("img", { name: "huevo" });
    expect(allergenIcon).toHaveAttribute("src", "/alergenos/huevo.svg");
    expect(screen.queryByRole("heading", { name: "Gazpacho andaluz" })).not.toBeInTheDocument();
  });

  it("displays the allergen caution", () => {
    render(<MenuSection menu={menu} loading={false} error="" />);

    expect(screen.getAllByText(/La información sobre alérgenos es orientativa/)).toHaveLength(1);
    expect(screen.getAllByText(/confirma siempre cualquier alergia con nuestro equipo/)).toHaveLength(1);
  });
});
