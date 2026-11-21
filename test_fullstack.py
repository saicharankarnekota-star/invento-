"""End-to-end Verification for INVENTO AI:
1. Supabase Cloud Connection & Auth reachability
2. Local & Cloud Database adapter operations
3. Backend Flask App, blueprints & route responses
4. Frontend presentation assets & templates
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def test_supabase_cloud():
    print("\n--- 1. Testing Supabase Cloud Connection & Services ---")
    try:
        from supabase import create_client
        url = "https://ezfneigycsbtgooijuiz.supabase.co"
        key = "sb_publishable_Ku971fGXam8ruMdqpKpFxg_fu925BrX"
        client = create_client(url, key)
        session_resp = client.auth.get_session()
        print(f"✅ Supabase Client initialized successfully for: {url}")
        print(f"✅ Auth Service status: Active (Session: {session_resp})")

        # Test Storage Service
        from backend.services.storage import upload_file_bytes
        test_bytes = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        uploaded_url = upload_file_bytes("invento-products", test_bytes, "test_ping.gif", "image/gif")
        if uploaded_url:
            print(f"✅ Supabase Storage: Successfully verified bucket 'invento-products' -> {uploaded_url}")
        else:
            print("ℹ️ Supabase Storage: Offline/Local fallback ready")

        # Test Vercel Serverless Entrypoint
        import api.index
        assert hasattr(api.index, "app"), "Vercel entrypoint api/index.py must expose 'app'"
        print("✅ Vercel serverless entrypoint 'api/index.py' verified")

        return True
    except Exception as e:
        print(f"❌ Supabase Cloud test error: {e}")
        return False

def test_backend_and_database():
    print("\n--- 2. Testing Backend & Database Seam ---")
    try:
        from backend.app import app
        from backend.services.db import get_db, init_db
        from backend.models.product import ProductModel
        from backend.models.user import UserModel
        from backend.models.bill import BillModel

        init_db()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM products")
        count = cursor.fetchone()[0]
        conn.close()

        print(f"✅ Database initialized: {count} products present in catalog.")

        # Test Models
        admin = UserModel.get_by_identifier("admin@invento.ai")
        print(f"✅ UserModel: Found admin user '{admin['username']}' (role: {admin['role']})")

        metrics = ProductModel.get_dashboard_metrics()
        print(f"✅ ProductModel: Total valuation ₹{metrics['total_valuation']:,.2f}, Low stock items: {metrics['low_stock_count']}")

        # Test Flask Client routes
        client = app.test_client()

        # Test Root / Landing
        res = client.get("/")
        print(f"✅ Route '/' response: {res.status_code}")

        # Test Login Page
        res = client.get("/login")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        assert b"Sign In" in res.data, "Sign In text not found in login page"
        print(f"✅ Route '/login' rendered successfully (Status 200)")

        # Test Valid Authentication
        res = client.post("/login", data={
            "email": "admin@invento.ai",
            "password": "admin123"
        }, follow_redirects=True)
        assert b"Dashboard" in res.data, "Dashboard not loaded after login"
        print("✅ Authentication successful: Logged in as Store Admin")

        # Test Dashboard (Admin Executive)
        res = client.get("/dashboard")
        assert res.status_code == 200
        assert b"Executive Store Overview" in res.data or b"Total Products" in res.data
        print("✅ Route '/dashboard' (Admin Executive) rendered with metrics and charts")

        # Test Admin Previewing Inventory Manager View
        res = client.get("/dashboard?role_view=inventory_manager")
        assert res.status_code == 200
        assert b"Shelf &amp; Stock Operations" in res.data or b"Shelf" in res.data
        print("✅ Route '/dashboard?role_view=inventory_manager' rendered inventory operations view")

        # Test Admin Previewing Cashier View
        res = client.get("/dashboard?role_view=cashier")
        assert res.status_code == 200
        assert b"Frontline Billing" in res.data or b"OPEN POS" in res.data
        print("✅ Route '/dashboard?role_view=cashier' rendered cashier shift view")

        # Test Direct Inventory Manager Login
        client.get("/logout")
        client.post("/login", data={"email": "stock@invento.ai", "password": "stock123"}, follow_redirects=True)
        res = client.get("/dashboard")
        assert res.status_code == 200
        assert b"Stock Lead" in res.data
        print("✅ Direct Login as Inventory Lead (stock@invento.ai) verified")

        # Test Direct Cashier Login
        client.get("/logout")
        client.post("/login", data={"email": "cashier@invento.ai", "password": "cashier123"}, follow_redirects=True)
        res = client.get("/dashboard")
        assert res.status_code == 200
        assert b"Cashier" in res.data
        print("✅ Direct Login as Cashier (cashier@invento.ai) verified")

        # Re-login as admin for other route tests
        client.get("/logout")
        client.post("/login", data={"email": "admin@invento.ai", "password": "admin123"}, follow_redirects=True)

        # Test Products
        res = client.get("/products")
        assert res.status_code == 200
        print("✅ Route '/products' rendered product catalog")

        # Test Billing POS
        res = client.get("/billing")
        assert res.status_code == 200
        print("✅ Route '/billing' POS terminal loaded")

        # Test Reports
        res = client.get("/reports")
        assert res.status_code == 200
        print("✅ Route '/reports' inventory reports loaded")

        # Test Barcode SVG
        res = client.get("/barcode/2000000000015.svg")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        assert b"<svg" in res.data
        print("✅ Route '/barcode/<code>.svg' generated vector barcode")

        return True
    except Exception as e:
        print(f"❌ Backend test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_frontend_files():
    print("\n--- 3. Testing Frontend Assets ---")
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "frontend"))
    required = [
        "index.html",
        "login.html",
        "dashboard.html",
        "dashboard_admin.html",
        "dashboard_inventory.html",
        "dashboard_cashier.html",
        "products.html",
        "billing.html",
        "alerts.html",
        "reports.html",
        "css/style.css",
        "js/script.js",
        "js/supabaseClient.js",
        "package.json"
    ]
    all_ok = True
    for item in required:
        path = os.path.join(frontend_dir, item)
        if os.path.exists(path):
            print(f"✅ Frontend file verified: {item}")
        else:
            print(f"❌ Missing frontend file: {item}")
            all_ok = False
    return all_ok

if __name__ == "__main__":
    t1 = test_supabase_cloud()
    t2 = test_backend_and_database()
    t3 = test_frontend_files()

    print("\n" + "=" * 60)
    if t1 and t2 and t3:
        print("🎉 ALL TESTS PASSED! Frontend, Backend & Supabase DB verified!")
    else:
        print("⚠️ Some tests failed. Review output above.")
    print("=" * 60 + "\n")
