import { useEffect, useState } from "react";
import EmailIcon from "@mui/icons-material/Email";
import GitHubIcon from "@mui/icons-material/GitHub";
import LinkedInIcon from "@mui/icons-material/LinkedIn";
import ChatWidget from "./components/ChatWidget";
import MenuSection from "./components/MenuSection";
import ReservationSection from "./components/ReservationSection";
import { getMenu } from "./services/api";

export default function App() {
  const [menu, setMenu] = useState([]);
  const [loading, setLoading] = useState(true);
  const [menuError, setMenuError] = useState("");

  useEffect(() => {
    getMenu()
      .then(setMenu)
      .catch(() => setMenuError("No pudimos cargar la carta. Inténtalo de nuevo más tarde."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="site-shell">
      <header className="site-header">
        <a className="brand" href="#inicio" aria-label="RAGtaurant, inicio">
          <span className="brand-mark" aria-hidden="true">R</span>
          <span>RAG<span>taurant</span></span>
        </a>
        <nav aria-label="Navegación principal">
          <a href="#carta">La carta</a>
        </nav>
        <a className="header-booking" href="#reservas">Reserva tu mesa <span aria-hidden="true">↗</span></a>
      </header>

      <main>
        <section className="hero" id="inicio">
          <div className="hero-shade" />
          <div className="hero-content">
            <p className="eyebrow">San Juan del Puerto · Huelva</p>
            <h1>El sur se sirve<br /><em>en la mesa.</em></h1>
            <p className="hero-copy">Producto de aquí, fuego lento y el placer de compartir. Cocina andaluza con alma choquera.</p>
            <a className="button button-light" href="#carta">Descubre nuestra carta <span aria-hidden="true">↓</span></a>
          </div>
          <span className="hero-caption">Una mesa, muchas historias.</span>
        </section>

        <section className="intro" aria-label="Nuestra cocina">
          <p className="eyebrow">Cocina honesta, sabor a sur</p>
          <h2>De la huerta, del mar<br />y de nuestra memoria.</h2>
          <p>Recetas de siempre, ingredientes de temporada y una mesa abierta para todos.</p>
        </section>

        <MenuSection menu={menu} loading={loading} error={menuError} />
        <ReservationSection />
      </main>

      <footer className="site-footer">
        <a className="brand brand-footer" href="#inicio"><span className="brand-mark" aria-hidden="true">R</span><span>RAG<span>taurant</span></span></a>
        <p>Hecho con calma por Patricio Rodríguez.</p>
        <div className="footer-social">
          <a href="mailto:patriciorodriguezramirez@gmail.com" aria-label="Enviar un email a Patricio Rodríguez"><EmailIcon /></a>
          <a href="https://www.linkedin.com/in/patriciorr" target="_blank" rel="noopener noreferrer" aria-label="LinkedIn de Patricio Rodríguez"><LinkedInIcon /></a>
          <a href="https://github.com/patriciorr" target="_blank" rel="noopener noreferrer" aria-label="GitHub de Patricio Rodríguez"><GitHubIcon /></a>
        </div>
      </footer>
      <ChatWidget />
    </div>
  );
}
