export const ADMIN_HOME_PATH = '/admin';
export const ADMIN_LOGIN_PATH = '/admin/login';

type ReplaceCapableRouter = {
  replace: (href: string) => void;
};

export function redirectToAdminLogin(router: ReplaceCapableRouter) {
  router.replace(ADMIN_LOGIN_PATH);
}

export function hardRedirectToAdminLogin() {
  if (typeof window !== 'undefined') {
    window.location.replace(ADMIN_LOGIN_PATH);
  }
}
