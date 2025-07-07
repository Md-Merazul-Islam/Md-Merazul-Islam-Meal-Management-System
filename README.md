![image](https://github.com/user-attachments/assets/e1877442-03b3-4ecc-a0fe-6ae9fc219a6e)



# 🍽️ Meal Management System

A comprehensive meal subscription and delivery management platform built with Django, featuring automated scheduling, payment processing, and multi-role management capabilities.

## 📋 Overview

This meal management system enables customers to subscribe to weekly or monthly meal plans with automated delivery scheduling. The platform supports multiple user roles including customers, admins, delivery personnel, and bakery staff, with integrated payment processing and intelligent delivery optimization.

## ✨ Key Features

### 🔐 User Management & Roles
- **Customer Role**: Subscribe to meal plans, manage orders, pause/cancel deliveries
- **Admin Role**: Manage subscriptions, approve/decline cancellations, oversee operations
- **Delivery Personnel**: Access delivery dashboard, export delivery lists (Excel/PDF)
- **Bakery Staff**: Receive advance order notifications (3 days ahead via email)

### 📅 Subscription Management
- **Flexible Plans**: Weekly and monthly subscription options
- **Meal Selection**: Choose products, quantities, and specific meals
- **Schedule Control**: Select delivery days and meal types
- **Order Tracking**: View all orders and subscription status
- **Smart Cancellation**: Pause or cancel deliveries for specific dates (tour/vacation mode)

### 💰 Payment & Pricing
- **Payment Gateways**: Integrated PayPal and Stripe
- **Loyalty Discount**: 10% discount for regular customers with terms agreement
- **Optimized Delivery Fees**: Intelligent delivery cost calculation
- **Automated Billing**: Recurring payments with Celery background tasks

### 🚚 Delivery Management
- **Area-Based Delivery**: Delivery personnel assigned to specific areas
- **Export Capabilities**: Generate delivery lists in Excel and PDF formats
- **Route Optimization**: Efficient delivery fee calculation
- **Real-time Tracking**: Monitor delivery status and updates

### 🎯 Advanced Features
- **Free Trial**: Admin-approved trial subscriptions for new customers
- **Automated Monitoring**: 
  - Subscription expiration tracking
  - Order expiration management
  - Automated payment processing
- **Background Tasks**: Celery and Celery Beat for scheduled operations
- **Caching**: Redis integration for improved performance
- **Contact & Support**: Built-in customer support system

## 🛠️ Technology Stack

### Backend
- **Framework**: Django (Python)
- **Task Queue**: Celery + Celery Beat
- **Database**: PostgreSQL (production), SQLite (development)
- **Cache**: Redis
- **API**: Django REST Framework

### Frontend
- **Framework**: Django Templates with Bootstrap
- **JavaScript**: jQuery for dynamic interactions
- **Styling**: Bootstrap 5 + Custom CSS

### Payment Integration
- **PayPal**: PayPal SDK
- **Stripe**: Stripe API
- ![image](https://github.com/user-attachments/assets/ce80ce8f-9fad-45d2-acc9-8990d40d85c4)


### Object Storage
-  **S3 oject storage 

### DevOps & Deployment
- **Containerization**: Docker & Docker Compose
- **Monitoring**: Logging and performance monitoring
- **Environment**: Production-ready configuration

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8+
- Docker & Docker Compose
- PostgreSQL
- Redis

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/meal-management-system.git
   cd meal-management-system
   ```

2. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Docker Setup**
   ```bash
   docker-compose up -d
   ```

4. **Database Migration**
   ```bash
   docker-compose exec web python manage.py migrate
   docker-compose exec web python manage.py createsuperuser
   ```

5. **Load Sample Data**
   ```bash
   docker-compose exec web python manage.py loaddata fixtures/sample_data.json
   ```

### Environment Variables
```env
# Django
SECRET_KEY=your-super-secret-key
DEBUG=True

# Database (PostgreSQL)
DB_NAME=meal_db
DB_USER=meal_user
DB_PASSWORD=meal_pass
DB_HOST=localhost

# Email
EMAIL_HOST_USER=youremail@example.com
EMAIL_HOST_PASSWORD=your-email-password
DEFAULT_FROM_EMAIL=youremail@example.com
ADMIN_EMAIL=admin@example.com
BEKARY_EMAIL=bakery@example.com

# DigitalOcean Spaces / AWS S3
AWS_S3_ENDPOINT_URL=https://nyc3.digitaloceanspaces.com
AWS_ACCESS_KEY_ID=your-do-access-key
AWS_SECRET_ACCESS_KEY=your-do-secret-key
AWS_STORAGE_BUCKET_NAME=your-bucket-name

# Stripe
STRIPE_TEST_SECRET_KEY=sk_test_abc123
STRIPE_TEST_PUBLIC_KEY=pk_test_abc123
STRIPE_ENDPOINT_SECRET=whsec_abc123

# PayPal
PAYPAL_TEST_CLIENT_ID=your-paypal-client-id
PAYPAL_TEST_SECRET_KEY=your-paypal-secret


```

## 📱 Usage

### For Customers
1. **Registration**: Sign up and choose subscription plan
2. **Meal Selection**: Browse and select meals with quantities
3. **Schedule Setup**: Choose delivery days and meal preferences
4. **Payment**: Complete payment via PayPal or Stripe
5. **Manage Orders**: View, pause, or cancel deliveries as needed

### For Admins
1. **Dashboard**: Monitor all subscriptions and orders
2. **Approval System**: Review and approve/decline cancellation requests
3. **Customer Management**: Handle free trial requests
4. **Analytics**: Track revenue, popular meals, and delivery metrics

### For Delivery Personnel
1. **Area Dashboard**: View assigned delivery areas
2. **Daily Routes**: Access optimized delivery lists
3. **Export Options**: Download delivery data in Excel/PDF
4. **Status Updates**: Mark deliveries as completed

### For Bakery Staff
1. **Advance Orders**: Receive email notifications 3 days ahead
2. **Production Planning**: Plan meals based on upcoming orders
3. **Inventory Management**: Track ingredient requirements

## 🔧 API Endpoints

### Authentication
- `POST /api/auth/login/` - User login
- `POST /api/auth/register/` - User registration
- `POST /api/auth/logout/` - User logout

### Subscriptions
- `GET /api/subscriptions/` - List user subscriptions
- `POST /api/subscriptions/` - Create new subscription
- `PUT /api/subscriptions/{id}/` - Update subscription
- `DELETE /api/subscriptions/{id}/` - Cancel subscription

### Orders
- `GET /api/orders/` - List orders
- `POST /api/orders/pause/` - Pause order for specific date
- `POST /api/orders/resume/` - Resume paused order

### Payments
- `POST /api/payments/paypal/` - Process PayPal payment
- `POST /api/payments/stripe/` - Process Stripe payment

## 🏗️ Architecture

```
![alt text](image.png)
```

## 🧪 Testing

```bash
# Run all tests
docker-compose exec web python manage.py test

# Run specific app tests
docker-compose exec web python manage.py test apps.subscriptions

# Coverage report
docker-compose exec web coverage run --source='.' manage.py test
docker-compose exec web coverage report
```

## 📊 Monitoring & Logging

- **Application Logs**: Structured logging with Django logging
- **Performance Monitoring**: Database query optimization
- **Error Tracking**: Comprehensive error logging
- **Health Checks**: Container health monitoring

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Django community for the excellent framework
- Celery team for reliable task processing
- PayPal and Stripe for payment processing APIs
- Bootstrap team for responsive UI components

## 📞 Support

For support, email mdmerazul@gmail.com or join our Slack channel.

---

**Built with ❤️ by the Meal Management Team**
