import { useMemo, useState } from "react";

const categories = [
  { id: "entrante", label: "Entrantes", countLabel: "Para empezar" },
  { id: "principal", label: "Principales", countLabel: "De la cocina" },
  { id: "postre", label: "Postres", countLabel: "Algo dulce" },
];

export default function MenuSection({ menu, loading, error }) {
  const [category, setCategory] = useState(categories[0].id);
  const dishes = useMemo(
    () => menu.filter((dish) => dish.category === category && dish.available !== false),
    [menu, category],
  );
  const selectedCategory = categories.find((item) => item.id === category);

  return (
    <section className="menu-section section-wrap" id="carta">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Sabores de temporada</p>
          <h2>Nuestra carta</h2>
        </div>
        <p className="section-aside">Una cocina sencilla, de producto y para compartir.</p>
      </div>

      <div className="category-tabs" role="tablist" aria-label="Categorías de la carta">
        {categories.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            id={`tab-${item.id}`}
            aria-selected={category === item.id}
            aria-controls={`panel-${item.id}`}
            className={category === item.id ? "category-tab active" : "category-tab"}
            onClick={() => setCategory(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div role="tabpanel" id={`panel-${category}`} aria-labelledby={`tab-${category}`}>
        <div className="dish-grid">
          {loading && <p className="status-message" role="status">Cargando la carta…</p>}
          {!loading && error && <p className="status-message error-message" role="alert">{error}</p>}
          {!loading && !error && dishes.length === 0 && (
            <p className="status-message">{selectedCategory.countLabel}: pronto encontrarás nuevas propuestas.</p>
          )}
          {!loading && !error && dishes.map((dish) => (
            <article className="dish-card" key={dish.id}>
              <div className="dish-photo-wrap">
                {dish.image_url ? (
                  <img className="dish-photo" src={dish.image_url} alt={dish.name} loading="lazy" />
                ) : (
                  <div className="dish-photo dish-photo-fallback" role="img" aria-label={dish.name}>R</div>
                )}
                {(dish.is_vegan || dish.is_vegetarian) && (
                  <span className="dish-diet-badge">
                    {dish.is_vegan ? "Vegano" : "Vegetariano"}
                  </span>
                )}
              </div>
              <div className="dish-body">
                <div className="dish-title-row">
                  <h3>{dish.name}</h3>
                  <span className="dish-price">{Number(dish.price).toFixed(2)} €</span>
                </div>
                <p className="dish-description">{dish.description}</p>
                {dish.allergens?.length > 0 && (
                  <div className="dish-allergens">
                    <strong>Alérgenos:</strong>
                    <ul className="allergen-icons" aria-label="Alérgenos del plato">
                      {dish.allergens.map((allergen) => (
                        <li key={allergen}>
                          <img
                            src={`/alergenos/${encodeURIComponent(allergen)}.svg`}
                            alt={allergen}
                            title={allergen}
                            loading="lazy"
                          />
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </article>
          ))}
        </div>
      </div>
      <p className="allergen-note">
        <strong>¿Tienes alguna alergia?</strong> La información sobre alérgenos es orientativa. Aunque cuidamos cada preparación, puede haber trazas o cambios de ingredientes. Por favor, confirma siempre cualquier alergia con nuestro equipo antes de pedir.
      </p>
    </section>
  );
}
