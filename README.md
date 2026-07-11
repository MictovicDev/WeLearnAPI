# Tutor Booking Platform API

A Django REST Framework marketplace connecting students with verified tutors for online and onsite sessions.

## Stack
- Django 4.2 + DRF
- JWT auth via `djangorestframework-simplejwt`
- OpenAPI docs via `drf-spectacular`
- Filtering via `django-filter`

## Setup

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## API Docs
- Swagger UI: http://localhost:8000/api/docs/
- ReDoc:       http://localhost:8000/api/redoc/
- Schema:      http://localhost:8000/api/schema/

## Key Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| POST | /api/v1/auth/login/ | Login, get JWT tokens |
| POST | /api/v1/auth/refresh/ | Refresh access token |
| POST | /api/v1/users/register/ | Register student or tutor |
| GET/PATCH | /api/v1/users/me/ | Own profile |
| POST | /api/v1/users/logout/ | Blacklist refresh token |
| GET | /api/v1/tutors/ | Discover verified tutors |
| GET | /api/v1/tutors/{id}/ | Tutor detail |
| POST | /api/v1/tutors/my-profile/create/ | Create tutor profile |
| GET/PATCH | /api/v1/tutors/my-profile/ | Manage own profile |
| POST | /api/v1/tutors/my-profile/upload-verification/ | Submit ID docs |
| POST | /api/v1/tutors/{id}/verify/ | Admin: approve/reject |
| GET/POST | /api/v1/tutors/my/availability/ | Manage weekly slots |
| GET/POST | /api/v1/bookings/ | List / create bookings |
| GET | /api/v1/bookings/{id}/ | Booking detail |
| PATCH | /api/v1/bookings/{id}/respond/ | Tutor: accept/decline |
| PATCH | /api/v1/bookings/{id}/cancel/ | Cancel booking |
| PATCH | /api/v1/bookings/{id}/complete/ | Mark completed |
| GET/POST | /api/v1/reviews/ | List / submit reviews |
| GET/POST | /api/v1/conversations/ | List / start conversations |
| GET | /api/v1/conversations/{id}/messages/ | Read messages |
| POST | /api/v1/conversations/{id}/messages/send/ | Send message |

## Roles
- **student** — books sessions, submits reviews, starts conversations
- **tutor** — manages profile, availability, responds to bookings
- **admin** — verifies tutors, manages all users and bookings

## Tutor Flow
1. Register with role=tutor
2. POST /api/v1/tutors/my-profile/create/ — fill bio, subjects, rate, mode
3. POST /api/v1/tutors/my-profile/upload-verification/ — submit ID docs
4. Admin approves via POST /api/v1/tutors/{id}/verify/ with {"action": "approve"}
5. Profile becomes visible in discovery

## Production Notes
- Switch `SECRET_KEY` to env var
- Set `DEBUG=False`
- Configure PostgreSQL in DATABASES
- Set `ALLOWED_HOSTS` to your domain
- Run `collectstatic` and serve media via Nginx/S3
