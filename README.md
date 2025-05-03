
# FastHTML with Auth0 Example

This application demonstrates how to integrate **Auth0** authentication into a **FastHTML** app using **Auth0 Management API** and **Auth0 Authentication API**. It provides an example of logging in, checking user status (blocked or active), displaying user information, and managing active sessions.

## Requirements

Before running the app, you need to set up an **Auth0** account and configure your environment variables. This application uses `uv` as the package manager and runtime.

## Prerequisites

* Python 3.7+ (preferred 3.8 or newer)
* `uv` (Python package manager)
* Auth0 account

### Install Dependencies

1. Clone the repository:

   ```bash
   git clone https://github.com/78wesley/fasthtml-auth0
   cd fasthtml-auth0
   ```

2. Rename `.env.example` to `.env` and fill in the required Auth0 configuration:

   ```bash
   mv .env.example .env
   ```

   Now open the `.env` file and replace the placeholders with your Auth0 credentials:

   * `AUTH0_CLIENT_ID`: Your Auth0 Application Client ID.
   * `AUTH0_CLIENT_SECRET`: Your Auth0 Application Client Secret.
   * `AUTH0_DOMAIN`: Your Auth0 domain (e.g., `your-app.auth0.com`).
   * `AUTH0_CALLBACK_URL`: The URL where users will be redirected after authentication (typically something like `http://localhost:5001/callback`).
   * `AUTH0_AUDIENCE`: The audience for your Auth0 API (typically `https://<your-auth0-domain>/api/v2/`).

3. Make sure all the required environment variables are set correctly. If any of the variables are missing, the application will raise an error.

## Running the Application

Once the environment is configured, run the app with the following command:

```bash
uv run main.py
```

The application should now be accessible at `http://localhost:5001`.

### Auth0 Setup

To use this application, you will need to configure an Auth0 Application and API. Follow these steps:

1. **Create an Auth0 Account**
   Go to [Auth0](https://auth0.com/) and create an account if you don't already have one.

2. **Create a New Application**

   * Navigate to the **Applications** section in your Auth0 dashboard.
   * Create a **Regular Web Application** and note down the **Client ID** and **Client Secret**.

3. **Configure Callback URL**

   * In the settings tab, add the **Callback URL** (e.g., `http://localhost:5001/callback`).
   * Add the **Logout URL** (e.g., `http://localhost:5001/`).
   * Add the **Web Origins** (e.g., `http://localhost:5001/`).
   * Click on the **Save** button.

4. **Create an API**

   * Go to the **APIs** section in your Auth0 dashboard.
   * Create a new API. Set the **Audience** to a unique identifier, such as `https://<your-auth0-domain>/api/v2/`.
   * Note down the **Audience** URL as you will need it to configure your application.

5. **Configure API at the Application**
   * Go back to your Application and open the **APIs** tab.
   * Click on the arrow at the API and give the permissions
     - read:users
     - read:users_app_metadata (optional)

## Notes

* The application caches the Auth0 Management API token to optimize performance. The token is valid for one hour and will be refreshed automatically.
* The session management is handled using a simple list of active sessions.
* Blocked users are not allowed to access the application and will be redirected to the home page with an error message.

## Troubleshooting

* If you encounter errors related to missing environment variables, make sure that your `.env` file is correctly configured.
* If the token is expired, the application will automatically refresh it. Ensure that the Auth0 Management API credentials have the correct permissions to fetch the token.
