-- Create one database per service.
-- This script runs automatically on first postgres container start.
--
-- NOTE: previously this file created 7 databases (users, meals, orders,
-- payments, notifications, delivery, admin) but every service's
-- DATABASE_URL in docker-compose.yml pointed at the single shared
-- POSTGRES_DB (nutmeals_db) instead -- so all 7 sat empty/unused, and
-- catalog/inventory/crm/finance/logistics/manufacturing/seo/cart_checkout/
-- security/customer_commerce/procurement had no dedicated database at all.
-- This version creates a database for every service and docker-compose.yml
-- now points each service's DATABASE_URL at its own database.
-- `nutmeals_delivery` was removed since delivery-service does not exist
-- in this repository (referenced in the old compose file but has no code).

CREATE DATABASE nutmeals_users;
CREATE DATABASE nutmeals_meals;
CREATE DATABASE nutmeals_orders;
CREATE DATABASE nutmeals_payments;
CREATE DATABASE nutmeals_notifications;
CREATE DATABASE nutmeals_admin;
CREATE DATABASE nutmeals_admin_cms;
CREATE DATABASE nutmeals_catalog;
CREATE DATABASE nutmeals_inventory;
CREATE DATABASE nutmeals_crm;
CREATE DATABASE nutmeals_finance;
CREATE DATABASE nutmeals_logistics;
CREATE DATABASE nutmeals_manufacturing;
CREATE DATABASE nutmeals_seo;
CREATE DATABASE nutmeals_cart_checkout;
CREATE DATABASE nutmeals_security;
CREATE DATABASE nutmeals_customer_commerce;
CREATE DATABASE nutmeals_procurement;