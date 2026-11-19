import './FAQSection.css';

const faqs = [
  {
    question: '¿Cómo se usa esta web?',
    answer:
      'Puedes consultar la carta y preguntar al asistente virtual usando el botón de chat. El formulario de reservas sirve para probar la experiencia con datos ficticios.',
  },
  {
    question: '¿Tengo que introducir datos personales?',
    answer:
      'No necesitas datos personales para navegar por la web ni para hacer preguntas en el chat. El formulario de reserva solicita nombre, correo electrónico, teléfono, fecha, hora y número de comensales. Como es una demostración, usa datos ficticios.',
  },
  {
    question: '¿Qué ocurre con la información que envío?',
    answer:
      'Los mensajes del chat y el texto utilizado para la búsqueda se procesan con Google Gemini. La información de las reservas se guarda en MongoDB. No introduzcas datos personales reales; no se ha verificado el plazo de retención de los servicios externos.',
  },
  {
    question: '¿El restaurante y la información son reales?',
    answer:
      'No. Este es un proyecto personal de portfolio y el restaurante es ficticio. La carta, los precios, las fotografías y la información sobre alérgenos son ilustrativos; no uses esta demostración para hacer una reserva real ni para tomar decisiones sobre alergias.',
  },
];

function FAQSection() {
  return (
    <section
      className="faq-section"
      id="preguntas"
      aria-labelledby="faq-title"
    >
      <div className="faq-section__content">
        <h2 id="faq-title">Preguntas frecuentes</h2>
        <div className="faq-section__list">
          {faqs.map(({ question, answer }) => (
            <details className="faq-section__item" key={question}>
              <summary>{question}</summary>
              <p>{answer}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}

export default FAQSection;
