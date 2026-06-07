package com.aicoach.realtime;

import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;

import java.util.Map;

@Service
public class InterviewRealtimeService {
    private final SimpMessagingTemplate messagingTemplate;

    public InterviewRealtimeService(SimpMessagingTemplate messagingTemplate) {
        this.messagingTemplate = messagingTemplate;
    }

    public void publish(long interviewId, String type, Object payload) {
        messagingTemplate.convertAndSend("/topic/interview." + interviewId, Map.of(
                "type", type,
                "payload", payload
        ));
    }
}
