package org.tanzu.ssotile.security;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.annotation.Order;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    private static final Logger log = LoggerFactory.getLogger(SecurityConfig.class);

    @Bean
    @Order(1)
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        log.info("Configuring SecurityFilterChain - requiring authentication for all requests");
        
        http
            .securityMatcher("/**")
            .authorizeHttpRequests(auth -> auth
                    .anyRequest().authenticated()
            )
            .oauth2Login(Customizer.withDefaults());
        
        log.info("SecurityFilterChain configured with OAuth2 login");
        return http.build();
    }
}
