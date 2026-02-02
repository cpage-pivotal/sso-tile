package org.tanzu.ssotile.security;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.boot.autoconfigure.condition.ConditionalOnCloudPlatform;
import org.springframework.boot.cloud.CloudPlatform;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.oauth2.client.registration.ClientRegistration;
import org.springframework.security.oauth2.client.registration.ClientRegistrationRepository;
import org.springframework.security.oauth2.client.registration.InMemoryClientRegistrationRepository;
import org.springframework.security.oauth2.core.AuthorizationGrantType;
import org.springframework.security.oauth2.core.ClientAuthenticationMethod;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Configures OAuth2 client registration from Cloud Foundry VCAP_SERVICES.
 * This reads SSO credentials from the bound p-identity service instance.
 */
@Configuration
@ConditionalOnCloudPlatform(CloudPlatform.CLOUD_FOUNDRY)
public class SsoClientConfiguration {

    private static final Logger log = LoggerFactory.getLogger(SsoClientConfiguration.class);

    @Bean
    public ClientRegistrationRepository clientRegistrationRepository() {
        String vcapServices = System.getenv("VCAP_SERVICES");
        if (vcapServices == null || vcapServices.isBlank()) {
            throw new IllegalStateException("VCAP_SERVICES environment variable not found. Is the app bound to an SSO service?");
        }

        try {
            ObjectMapper mapper = new ObjectMapper();
            JsonNode root = mapper.readTree(vcapServices);
            
            // Look for p-identity service (Tanzu SSO)
            JsonNode ssoServices = root.get("p-identity");
            if (ssoServices == null || !ssoServices.isArray() || ssoServices.isEmpty()) {
                throw new IllegalStateException("No p-identity service found in VCAP_SERVICES. Bind the app to an SSO service instance.");
            }
            
            JsonNode ssoService = ssoServices.get(0);
            JsonNode credentials = ssoService.get("credentials");
            
            String clientId = credentials.get("client_id").asText();
            String clientSecret = credentials.get("client_secret").asText();
            String authDomain = credentials.get("auth_domain").asText();
            String authUri = authDomain + "/oauth/authorize";
            String tokenUri = authDomain + "/oauth/token";
            String userInfoUri = authDomain + "/userinfo";
            String jwkSetUri = authDomain + "/token_keys";
            
            log.info("Configuring SSO client with auth_domain: {}", authDomain);
            log.info("Client ID: {}", clientId);
            
            ClientRegistration registration = ClientRegistration.withRegistrationId("sso")
                    .clientId(clientId)
                    .clientSecret(clientSecret)
                    .clientAuthenticationMethod(ClientAuthenticationMethod.CLIENT_SECRET_BASIC)
                    .authorizationGrantType(AuthorizationGrantType.AUTHORIZATION_CODE)
                    .redirectUri("{baseUrl}/login/oauth2/code/{registrationId}")
                    .scope("openid")
                    .authorizationUri(authUri)
                    .tokenUri(tokenUri)
                    .userInfoUri(userInfoUri)
                    .jwkSetUri(jwkSetUri)
                    .userNameAttributeName("user_name")
                    .clientName("SSO")
                    .build();
            
            log.info("Created ClientRegistration for SSO with ID: sso");
            
            return new InMemoryClientRegistrationRepository(registration);
        } catch (Exception e) {
            throw new IllegalStateException("Failed to parse SSO credentials from VCAP_SERVICES", e);
        }
    }
}
