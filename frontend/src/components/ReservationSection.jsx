import { useEffect, useRef, useState } from "react";
import {
  cancelReservation,
  createReservation,
  getReservation,
  updateReservation,
} from "../services/api";

const serviceTimes = Array.from({ length: 23 }, (_, index) => {
  const minutes = 12 * 60 + index * 30;
  return `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;
});

function madridToday() {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/Madrid",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  return Object.fromEntries(parts.filter((part) => part.type !== "literal").map(({ type, value }) => [type, value]));
}

function dateRange() {
  const { year, month, day } = madridToday();
  const today = new Date(Date.UTC(Number(year), Number(month) - 1, Number(day)));
  const max = new Date(today);
  max.setUTCDate(max.getUTCDate() + 13);
  const format = (date) => date.toISOString().slice(0, 10);
  return { min: format(today), max: format(max) };
}

function formatSpanishDate(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value ?? "");
  return match ? `${match[3]}/${match[2]}/${match[1]}` : "";
}

function validateDate(value) {
  if (!value) return "Selecciona una fecha para la reserva.";
  const { min, max } = dateRange();
  if (value < min || value > max) return "Elige una fecha entre hoy y los próximos 13 días.";
  return "";
}

const monthNames = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
const weekdayNames = ["L", "M", "X", "J", "V", "S", "D"];

function ReservationDateInput({ name, value, onChange, min, max, required = false }) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef(null);
  const [minYear, minMonth] = min.split("-").map(Number);
  const [maxYear, maxMonth] = max.split("-").map(Number);
  const [view, setView] = useState(() => {
    const [year, month] = (value || min).split("-").map(Number);
    return { year, month };
  });

  useEffect(() => {
    if (!open) return undefined;
    const close = (event) => {
      if (!wrapRef.current?.contains(event.target)) setOpen(false);
    };
    const onKey = (event) => event.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const iso = (day) => `${view.year}-${String(view.month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
  const daysInMonth = new Date(view.year, view.month, 0).getDate();
  const offset = (new Date(view.year, view.month - 1, 1).getDay() + 6) % 7;
  const canPrev = view.year * 12 + view.month > minYear * 12 + minMonth;
  const canNext = view.year * 12 + view.month < maxYear * 12 + maxMonth;
  const shift = (delta) => setView(({ year, month }) => {
    const index = year * 12 + month - 1 + delta;
    return { year: Math.floor(index / 12), month: (index % 12) + 1 };
  });

  function pick(day) {
    onChange({ target: { name, value: iso(day) } });
    setOpen(false);
  }

  return (
    <div className="date-input-wrap" ref={wrapRef} onClick={(event) => event.preventDefault()}>
      <input type="hidden" name={name} value={value} required={required} readOnly />
      <button
        type="button"
        className={value ? "date-trigger" : "date-trigger date-input-placeholder"}
        aria-label="Fecha (día, mes y año)"
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        <span>{value ? formatSpanishDate(value) : "DD/MM/AAAA"}</span>
        <span aria-hidden="true">📅</span>
      </button>
      {open && (
        <div className="date-popover" role="dialog" aria-label="Calendario de reservas">
          <div className="date-popover-head">
            <button type="button" aria-label="Mes anterior" disabled={!canPrev} onClick={() => shift(-1)}>‹</button>
            <strong>{monthNames[view.month - 1]} {view.year}</strong>
            <button type="button" aria-label="Mes siguiente" disabled={!canNext} onClick={() => shift(1)}>›</button>
          </div>
          <div className="date-grid">
            {weekdayNames.map((day) => <span key={day} className="date-weekday">{day}</span>)}
            {Array.from({ length: offset }, (_, index) => <span key={`blank-${index}`} />)}
            {Array.from({ length: daysInMonth }, (_, index) => {
              const day = index + 1;
              const value_ = iso(day);
              const disabled = value_ < min || value_ > max;
              return (
                <button
                  type="button"
                  key={day}
                  disabled={disabled}
                  className={value_ === value ? "date-day selected" : "date-day"}
                  aria-label={`${day} de ${monthNames[view.month - 1]} de ${view.year}`}
                  aria-pressed={value_ === value}
                  onClick={() => pick(day)}
                >
                  {day}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function validateEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function validateSchedule({ date, time, guests }) {
  const dateError = validateDate(date);
  if (dateError) return dateError;
  if (!time) return "Selecciona una hora para la reserva.";
  if (!Number.isInteger(Number(guests)) || Number(guests) < 1 || Number(guests) > 20) {
    return "Indica entre 1 y 20 comensales.";
  }
  return "";
}

function errorMessage(error) {
  const detail = error?.response?.data?.detail;
  const translate = (message) => {
    const translations = [
      [/reservation not found/i, "No hemos encontrado una reserva con esos datos. Comprueba el código, el correo y el teléfono."],
      [/a reservation already exists/i, "Ya existe una reserva para esos datos de contacto en esa fecha."],
      [/reservations must be within the next 14 days/i, "Elige una fecha entre hoy y los próximos 13 días."],
      [/reservations cannot be made for a time that has passed/i, "Esa hora ya ha pasado. Elige otro turno."],
      [/reservations are available from 12:00 to 23:00/i, "Las reservas están disponibles de 12:00 a 23:00."],
      [/reservations are available on the half-hour/i, "Elige una hora en punto o y media."],
      [/cancelled reservations cannot be modified/i, "No se pueden modificar reservas canceladas."],
      [/enter a valid phone number/i, "Introduce un número de teléfono válido."],
      [/valid email address/i, "Introduce un correo electrónico válido."],
      [/internal server error|internal database error/i, "No se pudo completar la operación. Inténtalo de nuevo más tarde."],
    ];
    return translations.find(([pattern]) => pattern.test(message))?.[1] ?? message;
  };
  if (Array.isArray(detail)) {
    return detail.map((item) => {
      const message = translate(item.message ?? item.msg ?? "");
      return message === "Field required" ? "Este campo es obligatorio." : message;
    }).join(" ");
  }
  if (typeof detail === "string") return translate(detail);
  return "No se pudo completar la operación. Comprueba los datos e inténtalo de nuevo.";
}

function ReservationFields({ value, onChange, prefix, validationMode = false }) {
  const range = dateRange();
  return (
    <>
      <label>
        Nombre
        <input name="customer_name" autoComplete="name" minLength={validationMode ? "2" : undefined} maxLength={validationMode ? "120" : undefined} required={validationMode} value={value.customer_name ?? ""} onChange={onChange} />
      </label>
      <div className="form-grid">
        <label>
          Correo electrónico
          <input name="email" type={validationMode ? "email" : "text"} autoComplete="email" required={validationMode} value={value.email ?? ""} onChange={onChange} />
        </label>
        <label>
          Teléfono
          <input name="phone" type="tel" autoComplete="tel" placeholder="+34 600 000 000" maxLength={validationMode ? "40" : undefined} required={validationMode} value={value.phone ?? ""} onChange={onChange} />
        </label>
      </div>
      <div className="form-grid">
        <label>
          Fecha (DD/MM/AAAA)
          <ReservationDateInput
            name="date"
            min={range.min}
            max={range.max}
            required={validationMode}
            value={value.date ?? ""}
            onChange={onChange}
          />
        </label>
        <label>
          Hora
          {validationMode ? (
            <select name="time" required value={value.time ?? ""} onChange={onChange}>
              <option value="">Elige una hora</option>
              {serviceTimes.map((time) => <option key={`${prefix}-${time}`} value={time}>{time}</option>)}
            </select>
          ) : (
            <select name="time" value={value.time ?? ""} onChange={onChange}>
              {serviceTimes.map((time) => <option key={`${prefix}-${time}`} value={time}>{time}</option>)}
            </select>
          )}
        </label>
      </div>
      <label>
        Número de comensales
        <input name="guests" type="number" min={validationMode ? "1" : undefined} max={validationMode ? "20" : undefined} step={validationMode ? "1" : undefined} required={validationMode} value={value.guests ?? ""} onChange={onChange} />
      </label>
    </>
  );
}

export default function ReservationSection() {
  const [booking, setBooking] = useState({ customer_name: "", email: "", phone: "", date: "", time: "", guests: "2" });
  const [lookup, setLookup] = useState({ reservation_id: "", email: "", phone: "" });
  const [reservation, setReservation] = useState(null);
  const [edit, setEdit] = useState({ date: "", time: "", guests: "" });
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const updateForm = (setter) => (event) => setter((previous) => ({ ...previous, [event.target.name]: event.target.value }));
  const contact = { email: lookup.email, phone: lookup.phone };

  async function run(action, successMessage) {
    setBusy(true);
    setStatus("");
    setError("");
    try {
      const result = await action();
      if (result) {
        setReservation(result);
        setEdit({ date: result.date, time: result.time, guests: String(result.guests) });
        setLookup((previous) => ({
          ...previous,
          reservation_id: result.reservation_id,
          email: result.email,
          phone: result.phone,
        }));
      }
      setStatus(successMessage);
      return result;
    } catch (requestError) {
      setError(errorMessage(requestError));
      return null;
    } finally {
      setBusy(false);
    }
  }

  function submitBooking(event) {
    event.preventDefault();
    const validationError = booking.customer_name.trim().length < 2
      ? "Escribe tu nombre (al menos 2 caracteres)."
      : booking.customer_name.trim().length > 120
        ? "El nombre no puede superar los 120 caracteres."
        : !validateEmail(booking.email)
          ? "Introduce un correo electrónico válido."
          : !booking.phone.trim()
            ? "Introduce un teléfono de contacto."
            : validateSchedule(booking);
    if (validationError) {
      setStatus("");
      setError(validationError);
      return;
    }
    run(
      () => createReservation({ ...booking, guests: Number(booking.guests) }),
      "¡Listo! Tu reserva está confirmada. Guarda el código para consultarla o modificarla.",
    );
  }

  function findReservation(event) {
    event.preventDefault();
    if (!lookup.reservation_id.trim() || !validateEmail(lookup.email) || !lookup.phone.trim()) {
      setStatus("");
      setError("Introduce el código de reserva, un correo válido y tu teléfono.");
      return;
    }
    run(() => getReservation(lookup.reservation_id.trim(), contact), "Hemos encontrado tu reserva.");
  }

  function saveChanges(event) {
    event.preventDefault();
    const validationError = validateSchedule(edit);
    if (validationError) {
      setStatus("");
      setError(validationError);
      return;
    }
    run(
      async () => {
        const result = await updateReservation(
          lookup.reservation_id.trim(),
          { date: edit.date, time: edit.time, guests: Number(edit.guests) },
          contact,
        );
        setReservation(result);
        return result;
      },
      "Los cambios de tu reserva se han guardado.",
    );
  }

  function cancel() {
    run(async () => {
      await cancelReservation(lookup.reservation_id.trim(), contact);
      setReservation((previous) => ({ ...previous, status: "cancelled" }));
      return null;
    }, "Tu reserva ha sido cancelada.");
  }

  return (
    <section className="reservation-section" id="reservas">
      <div className="reservation-inner">
        <div className="reservation-copy">
          <p className="eyebrow">Una mesa te espera</p>
          <h2>Nos vemos<br /><em>en el sur.</em></h2>
          <p>Reserva tu momento para compartir. Si necesitas hacer cambios, podrás gestionar tu reserva con tu código y tus datos de contacto.</p>
          <p className="hours-note">Todos los días · 12:00-23:00 · Turnos cada media hora</p>
        </div>

        <div className="reservation-panels">
          <form className="reservation-card reservation-create" noValidate onSubmit={submitBooking}>
            <h3>Reserva una mesa</h3>
            <p className="form-intro">Hasta 20 personas · Con 14 días de antelación</p>
            <ReservationFields value={booking} onChange={updateForm(setBooking)} prefix="booking" validationMode />
            <button className="button button-dark" type="submit" disabled={busy}>Confirmar reserva <span aria-hidden="true">→</span></button>
          </form>

          <div className="reservation-card manage-card">
            <h3>Gestiona tu reserva</h3>
            <p className="form-intro">Necesitamos tu código de reserva, correo y teléfono.</p>
            <form className="reservation-lookup" noValidate onSubmit={findReservation}>
              <label>
                Código de reserva
                <input name="reservation_id" placeholder="RES-XXXXXXXX" required value={lookup.reservation_id} onChange={updateForm(setLookup)} />
              </label>
              <label>
                Correo electrónico
                <input name="email" type="email" autoComplete="email" required value={lookup.email} onChange={updateForm(setLookup)} />
              </label>
              <label>
                Teléfono
                <input name="phone" type="tel" autoComplete="tel" placeholder="+34 600 000 000" maxLength="40" required value={lookup.phone} onChange={updateForm(setLookup)} />
              </label>
              <button className="button button-outline" type="submit" disabled={busy}>Consultar reserva</button>
            </form>

            {reservation && (
              <div className="reservation-details" aria-live="polite">
                <p><strong>{reservation.customer_name}</strong> · {reservation.guests} personas</p>
                <p>{formatSpanishDate(reservation.date)} a las {reservation.time} · Código {reservation.reservation_id}</p>
                <p>Estado: {reservation.status === "cancelled" ? "cancelada" : "confirmada"}</p>
                {reservation.status !== "cancelled" && (
                  <form className="reservation-edit" noValidate onSubmit={saveChanges}>
                    <p className="edit-heading">Modificar fecha, hora o comensales</p>
                    <div className="form-grid">
                      <label>Fecha (DD/MM/AAAA)<ReservationDateInput name="date" min={dateRange().min} max={dateRange().max} required value={edit.date} onChange={updateForm(setEdit)} /></label>
                      <label>Hora<select name="time" required value={edit.time} onChange={updateForm(setEdit)}>{serviceTimes.map((time) => <option key={`edit-${time}`} value={time}>{time}</option>)}</select></label>
                    </div>
                    <label>Comensales<input name="guests" type="number" min="1" max="20" step="1" required value={edit.guests} onChange={updateForm(setEdit)} /></label>
                    <div className="reservation-actions">
                      <button className="button button-dark" type="submit" disabled={busy}>Guardar cambios</button>
                      <button className="button button-danger" type="button" disabled={busy} onClick={cancel}>Cancelar reserva</button>
                    </div>
                  </form>
                )}
              </div>
            )}
          </div>

          {status && <p className="form-feedback success-message" role="status">{status}</p>}
          {error && <p className="form-feedback error-message" role="alert">{error}</p>}
        </div>
      </div>
    </section>
  );
}
