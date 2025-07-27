<p align="center">
  <img src="assets/header.jpg" alt="Project Logo">
</p>
<p align="center" style="font-size: small;">Logo designed using <a href="https://canva.com">Canva</a></p>

## Project Description

Dentist Friend is an advanced dental practice management solution designed specifically for dental professionals in rural or remote areas where access to such systems is limited or prohibitively expensive. This comprehensive platform streamlines various aspects of dental practice management, making it easier for dentists to manage patient treatment plans, inventory, and communication smoothly.

### Key Features

- **Patient Management**:  Register patients, search records, and manage treatments with dental charts, procedures,
cost summaries, and PDF export.

- **Inventory Management**: Add, remove, and modify inventory items with alerts for low stock and expiring items.

- **Scheduling System**: Efficiently manage appointments, view available time slots, and send automated reminders for upcoming visits.

### Disclaimer

Please note that **Dentist Friend** is not intended to replace or infringe upon any existing commercial dental management software. Our goal is to offer a **free, open-source alternative** that emphasizes simplicity, accessibility, and affordability, especially for dental professionals in underserved or remote areas. We aim to provide a tool that simplifies the dental practice management experience without competing with or copying established products in the industry.

## System Architecture

<p align="center">
  <img src="assets/architecture.png" alt="System Architecture">
</p>

---

- **Streamlit UI:** An interactive and user-friendly interface for managing patient treatment plans, inventory, and communication. This UI is designed to allow dental professionals to seamlessly navigate the platform and manage all the core functionalities from one place.

- **Google Firestore Database:** A secure and scalable backend for storing patient and inventory data. Firestore provides real-time synchronization across devices and ensures that all data remains up-to-date and consistent across all users.

- **Cloudinary:** A cloud-based media management service for efficient storage and delivery of dental images, X-rays, and other clinical media files.

- **Mailgun:** An email automation service used for sending low stock and expiry alerts to ensure timely inventory management and minimize disruptions to practice operations.

The application is deployed via Docker on Digital Ocean App Platform.

## License

This project is licensed under the [MIT License](LICENSE).

## Authors

[Dr. Noor Hebbal](https://github.com/dent-noor) - [Areeb Ahmed](https://github.com/areebahmeddd)
