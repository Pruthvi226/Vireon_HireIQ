export function roleHome(role) {
  if (role === "ADMIN") return "/admin";
  if (role === "CANDIDATE") return "/candidate";
  return "/recruiter";
}
