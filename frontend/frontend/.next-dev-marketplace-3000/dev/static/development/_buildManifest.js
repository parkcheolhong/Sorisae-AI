self.__BUILD_MANIFEST = {
  "__rewrites": {
    "afterFiles": [
      {
        "source": "/api/backend-proxy/:path*"
      },
      {
        "source": "/api/:path*"
      },
      {
        "source": "/docs"
      },
      {
        "source": "/openapi.json"
      }
    ],
    "beforeFiles": [],
    "fallback": []
  },
  "sortedPages": [
    "/_app",
    "/_error"
  ]
};self.__BUILD_MANIFEST_CB && self.__BUILD_MANIFEST_CB()