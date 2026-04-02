import Header from "./Header";
import { Outlet } from "react-router-dom";

function Layout() {
  return (
    <div className="app-shell">
      <Header />

      <main className="container page-shell">
        <Outlet />
      </main>
    </div>
  );
}

export default Layout;