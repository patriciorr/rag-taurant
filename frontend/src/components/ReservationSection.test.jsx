import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ReservationSection from "./ReservationSection";

const api = vi.hoisted(() => ({
  createReservation: vi.fn(),
  getReservation: vi.fn(),
  updateReservation: vi.fn(),
  cancelReservation: vi.fn(),
}));

vi.mock("../services/api", () => api);

const reservation = {
  reservation_id: "RES-12345678",
  customer_name: "Ana Pérez",
  email: "ana@example.com",
  phone: "+34612345678",
  date: "",
  time: "18:30",
  guests: 2,
  status: "confirmed",
};

function dateInDays(days) {
  const parts = Object.fromEntries(new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/Madrid",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date()).filter((part) => part.type !== "literal").map(({ type, value }) => [type, value]));
  const date = new Date(Date.UTC(Number(parts.year), Number(parts.month) - 1, Number(parts.day)));
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

function spanishDate(isoDate) {
  const [year, month, day] = isoDate.split("-");
  return `${day}/${month}/${year}`;
}

const monthNames = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];

async function pickDate(user, scope, isoDate) {
  const [year, month, day] = isoDate.split("-").map(Number);
  const container = document.querySelector(scope);
  await user.click(container.querySelector(".date-trigger"));
  const label = `${day} de ${monthNames[month - 1]} de ${year}`;
  if (!container.querySelector(`[aria-label="${label}"]`)) {
    await user.click(container.querySelector('[aria-label="Mes siguiente"]'));
  }
  await user.click(container.querySelector(`[aria-label="${label}"]`));
}

describe("ReservationSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("creates a reservation and displays the returned confirmation", async () => {
    const user = userEvent.setup();
    api.createReservation.mockResolvedValue(reservation);
    render(<ReservationSection />);

    await user.type(screen.getByLabelText("Nombre"), "Ana Pérez");
    await user.type(document.querySelector(".reservation-create [name=email]"), "ana@example.com");
    await user.type(document.querySelector(".reservation-create [name=phone]"), "+34612345678");
    await pickDate(user, ".reservation-create", dateInDays(1));
    await user.selectOptions(document.querySelector(".reservation-create [name=time]"), "18:30");
    await user.clear(document.querySelector(".reservation-create [name=guests]"));
    await user.type(document.querySelector(".reservation-create [name=guests]"), "2");
    await user.click(screen.getByRole("button", { name: /Confirmar reserva/ }));

    await waitFor(() => expect(api.createReservation).toHaveBeenCalledWith(expect.objectContaining({
      customer_name: "Ana Pérez",
      email: "ana@example.com",
      phone: "+34612345678",
      date: dateInDays(1),
      time: "18:30",
      guests: 2,
    })));
    expect(document.querySelector(".reservation-create .date-trigger")).toHaveTextContent(spanishDate(dateInDays(1)));
    expect(document.querySelector(".reservation-create [name=guests]")).toHaveAttribute("min", "1");
    expect(document.querySelector(".reservation-create [name=guests]")).toHaveAttribute("max", "20");
    expect(screen.getByRole("status")).toHaveTextContent(/Tu reserva está confirmada/);
  });

  it("looks up, updates and cancels a reservation with the required contact headers", async () => {
    const user = userEvent.setup();
    const currentReservation = { ...reservation, date: dateInDays(2) };
    api.getReservation.mockResolvedValue(currentReservation);
    const updatedDate = dateInDays(3);
    api.updateReservation.mockResolvedValue({ ...currentReservation, date: updatedDate, guests: 4, time: "19:00" });
    api.cancelReservation.mockResolvedValue(undefined);
    render(<ReservationSection />);

    await user.type(screen.getByLabelText("Código de reserva"), currentReservation.reservation_id);
    await user.type(document.querySelector(".reservation-lookup [name=email]"), currentReservation.email);
    await user.type(document.querySelector(".reservation-lookup [name=phone]"), currentReservation.phone);
    await user.click(screen.getByRole("button", { name: "Consultar reserva" }));

    await waitFor(() => expect(api.getReservation).toHaveBeenCalledWith(
      currentReservation.reservation_id,
      { email: currentReservation.email, phone: currentReservation.phone },
    ));
    expect(await screen.findByText(/Estado: confirmada/)).toBeInTheDocument();

    const dateInput = document.querySelector(".reservation-edit [name=date]");
    expect(dateInput).toHaveValue(currentReservation.date);
    await pickDate(user, ".reservation-edit", updatedDate);
    await user.selectOptions(document.querySelector(".reservation-edit [name=time]"), "19:00");
    await user.clear(document.querySelector(".reservation-edit [name=guests]"));
    await user.type(document.querySelector(".reservation-edit [name=guests]"), "4");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => expect(api.updateReservation).toHaveBeenCalledWith(
      currentReservation.reservation_id,
      expect.objectContaining({ date: updatedDate, time: "19:00", guests: 4 }),
      { email: currentReservation.email, phone: currentReservation.phone },
    ));
    expect(await screen.findByText(/Los cambios de tu reserva se han guardado/)).toBeInTheDocument();
    expect(screen.getByText(new RegExp(`${spanishDate(updatedDate)} a las 19:00`))).toBeInTheDocument();
    expect(document.querySelector(".reservation-edit .date-trigger")).toHaveTextContent(spanishDate(updatedDate));
    expect(document.querySelector(".reservation-edit [name=guests]")).toHaveAttribute("min", "1");
    expect(document.querySelector(".reservation-edit [name=guests]")).toHaveAttribute("max", "20");

    await user.click(screen.getByRole("button", { name: "Cancelar reserva" }));

    await waitFor(() => expect(api.cancelReservation).toHaveBeenCalledWith(
      currentReservation.reservation_id,
      { email: currentReservation.email, phone: currentReservation.phone },
    ));
    expect(await screen.findByText(/Tu reserva ha sido cancelada/)).toBeInTheDocument();
    expect(screen.getByText(/Estado: cancelada/)).toBeInTheDocument();
  });

  it("announces backend validation errors accessibly", async () => {
    const user = userEvent.setup();
    api.getReservation.mockRejectedValue({
      response: { data: { detail: "Reservation not found." } },
    });
    render(<ReservationSection />);
    await user.type(screen.getByLabelText("Código de reserva"), "RES-MISSING");
    await user.type(document.querySelector(".reservation-lookup [name=email]"), "ana@example.com");
    await user.type(document.querySelector(".reservation-lookup [name=phone]"), "+34612345678");
    await user.click(screen.getByRole("button", { name: "Consultar reserva" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("No hemos encontrado una reserva");
  });

  it("shows Spanish validation and requires choosing a date", async () => {
    const user = userEvent.setup();
    render(<ReservationSection />);

    await user.type(screen.getByLabelText("Nombre"), "Ana Pérez");
    await user.type(document.querySelector(".reservation-create [name=email]"), "ana@example.com");
    await user.type(document.querySelector(".reservation-create [name=phone]"), "+34612345678");
    await user.selectOptions(document.querySelector(".reservation-create [name=time]"), "18:30");
    await user.click(screen.getByRole("button", { name: /Confirmar reserva/ }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Selecciona una fecha para la reserva.");
    expect(api.createReservation).not.toHaveBeenCalled();
  });
});


describe("Spanish date calendar", () => {
  it("shows a Spanish calendar with only the 14 bookable days enabled", async () => {
    const user = userEvent.setup();
    render(<ReservationSection />);
    await user.click(document.querySelector(".reservation-create .date-trigger"));

    const popover = document.querySelector(".date-popover");
    expect(popover.textContent).toMatch(new RegExp(monthNames.join("|")));
    expect(popover.querySelectorAll(".date-day:not(:disabled)").length).toBeLessThanOrEqual(14);
    expect(screen.getByRole("button", { name: "Mes anterior" })).toBeDisabled();
  });
});
